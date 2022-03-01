//SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

struct StakeInfo 
{
    uint256 tokens;        // stake from tokens
    uint256 bonus;         // bonus stake
    uint256 timestamp;     // last time stake was increased / compounded
    uint256 withdrawn;     // amount of shares that an address has withdrawn
}

contract LavaStaking
{
    event  StakeIncrease(address indexed user, uint amount);
    event  StakeDecrease(address indexed user, uint amount);
    event  RewardsDistributed(address indexed funder, uint amount);

    ERC20 public immutable asset;
    ERC20 public immutable wavax;
    uint256 public totalSupply = 0;
    uint256 public shares = 0;
    mapping(address => StakeInfo) public stake;  
    uint128 private constant MULTIPLIER = type(uint128).max;
    uint8 public immutable decimals;


    constructor(ERC20 _asset, ERC20 _wavax) 
    {
        asset = _asset;
        wavax = _wavax;
        decimals = _asset.decimals();
    }

    /** 
    * @dev Balance is the sum of the tokens staked plus a time-based bonus  
    * @param account Account whose balance is requested.
    */
    function balanceOf(address account) public view returns (uint256)
    {
        return stake[account].tokens + stake[account].bonus;
    }

    /** 
    * @dev Distributes rewards to stakers.
    * @param amount Amount to be distributed.
    */
    function distribute(uint256 amount) public 
    {
        wavax.transferFrom(msg.sender, address(this), amount);
        uint256 supply = totalSupply;
        require(supply > 0, "staked supply == 0");
        if (amount > 0) {
            shares += amount * MULTIPLIER / supply;
            emit RewardsDistributed(msg.sender, amount);
        }
    }

    /**
    * @dev Returns the total amount of rewards a given address is able to withdraw.
    * @param account Address of recipient
    * @return A uint256 representing the rewards `account` can withdraw
    */
    function pendingRewards(address account) public view returns (uint256) 
    {
        uint256 pending = balanceOf(account) * (shares - stake[account].withdrawn) / MULTIPLIER;
        uint256 balance = wavax.balanceOf(address(this));
        return pending <= balance ? pending : balance;
    }

    /**
    * @dev Deposit additional stake and claim any existing rewards
    * @param amount additional amount to be staked (can be 0 to claim and compound)
    */
    function deposit(uint256 amount) public 
    {
        uint256 pending = pendingRewards(msg.sender);
        wavax.transfer(msg.sender, pending);

        StakeInfo memory s = stake[msg.sender];
        uint256 bonus = (block.timestamp - s.timestamp) * s.tokens / (365 days);  // bonus grows at 100% APR
        s.tokens += amount;
        s.bonus += bonus;
        s.timestamp = block.timestamp;
        s.withdrawn = shares;
        stake[msg.sender] = s;
        totalSupply += amount + bonus;

        emit StakeIncrease(msg.sender, amount + bonus);
        asset.transferFrom(msg.sender, address(this), amount);
    }

    /**
    * @dev Withdraw all stake, claim all pending rewards and burn all bonus stake
    */
    function withdrawAll() public 
    {
        uint256 pending = pendingRewards(msg.sender);
        wavax.transfer(msg.sender, pending);

        StakeInfo memory s = stake[msg.sender];
        uint256 tokens = s.tokens;
        uint256 total = s.tokens + s.bonus; 
        delete stake[msg.sender];
        totalSupply -= total;
        emit StakeDecrease(msg.sender, total);
        asset.transfer(msg.sender, tokens);
    }
}
