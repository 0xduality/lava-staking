import { 
  Contract, 
  ContractFactory 
} from "ethers"
import { ethers, network } from "hardhat"

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

const main = async(): Promise<any> => {

  await network.provider.request({
    method: "hardhat_reset",
    params: [
      {
        forking: {
          jsonRpcUrl: 'https://api.avax.network/ext/bc/C/rpc', 
          enabled: true,
          blockNumber: 7867551,
        },
      },
    ],
  });
  const [deployer] = await ethers.getSigners();
  console.log("Account balance:", (await deployer.getBalance()).toString());
}

main()
.then(() => process.exit(0))
.catch(error => {
  console.error(error)
  process.exit(1)
})
