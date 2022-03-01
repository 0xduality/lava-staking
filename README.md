# LAVA staking concept

The staking contract here implements revenue sharing among stakers of an asset.
The stake of each staker is determined both by the amount of tokens they are staking 
as well as the amount of time they have been staking. The latter provides a bonus
stake that accrues at 100% APR of the token stake. Depositing 100 tokens means
a stake of 100 immediately, 200 after one year, 300 after two years and so on...
Unstaking at any time, returns the original tokens to the staker and burns the bonus stake.

Revenue is distributed as WAVAX from the balance of the caller of `distribute`.

Users can compound their stake, add more tokens, and claim any rewards with `deposit`.

Users can unstake and receive any final rewards with `withdrawAll`.


## Prerequisites

### NodeJS and Yarn

First, install the LTS (long-term support) version of [nodejs](https://nodejs.org/en). This is `14.17.0` at the time of writing. NodeJS bundles `npm`.

Next, install [yarn](https://yarnpkg.com):

```zsh
npm install -g yarn
```

### Solidity and Avalanche

It is also helpful to have a basic understanding of [Solidity](https://docs.soliditylang.org) and [Avalanche](https://docs.avax.network).

## Dependencies

Clone the repository and install the necessary packages via `yarn`.

```zsh
$ yarn
```

## Hardhat Config

Hardhat uses `hardhat.config.js` as the configuration file. You can define tasks, networks, compilers and more in that file. For more information see [here](https://hardhat.org/config/).

In our repository we use a pre-configured file `hardhat.config.ts`. This file configures necessary network information to provide smooth interaction with Avalanche. There are also some pre-defined private keys for testing on a local test network.

## Hardhat Tasks

You can define custom hardhat tasks in `hardhat.config.ts`

## Documentation

There is a documentation under the Avalanche's official documentation repository:
[Using Hardhat with the Avalanche C-Chain](https://docs.avax.network/build/tutorials/smart-contracts/using-hardhat-with-the-avalanche-c-chain)
