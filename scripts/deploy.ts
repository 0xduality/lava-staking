import { Contract, ContractFactory } from "ethers"
import { ethers } from "hardhat"

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

const main = async(): Promise<any> => {

  const [deployer] = await ethers.getSigners();

  console.log("Deploying contracts with account:", deployer.address);

  console.log("Account balance:", (await deployer.getBalance()).toString());

  const LAVA: ContractFactory = await ethers.getContractFactory("MockLAVA")
	const lava: Contract = await LAVA.deploy()
	await lava.deployed()
  const lavaAddress = lava.address
	console.log(`LAVA deployed to: ${lavaAddress}`)

  const wavaxAddress = ethers.utils.getAddress("0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7")

  const LavaStaking: ContractFactory = await ethers.getContractFactory("LavaStaking")
  const ls: Contract = await LavaStaking.deploy(lavaAddress, wavaxAddress)
  await ls.deployed()
  console.log(`staking contract deployed to: ${ls.address}`)
}

main()
.then(() => process.exit(0))
.catch(error => {
  console.error(error)
  process.exit(1)
})
