# Web3 Development Environment Setup Guide

This guide provides complete setup instructions for all the tools and infrastructure needed for comprehensive Web3 smart contract security auditing and development.

## Prerequisites

- Linux, macOS, or WSL2 on Windows
- sudo/administrator access
- Stable internet connection
- At least 20GB free disk space

## 1. Development Environment

### Node.js (LTS)

```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc  # or ~/.zshrc
nvm install --lts
nvm use --lts

# Verify installation
node --version
npm --version
```

### Truffle

```bash
npm install -g truffle

# Verify installation
truffle version
```

### Hardhat

```bash
# Install in your project
npm install --save-dev hardhat

# Or globally
npm install -g hardhat

# Initialize a Hardhat project
npx hardhat init
```

### Foundry (Rust-based toolchain)

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash

# This installs foundryup
foundryup

# Verify installation
forge --version
cast --version
anvil --version
chisel --version
```

### VS Code with Solidity Extensions

```bash
# Download VS Code from https://code.visualstudio.com/

# Install Solidity extensions
code --install-extension JuanBlanco.solidity
code --install-extension tintinweb.solidity-visual-auditor
code --install-extension NomicFoundation.hardhat-solidity
```

### Ganache (Local Blockchain)

```bash
npm install -g ganache

# Or use Ganache UI
# Download from https://trufflesuite.com/ganache/
```

## 2. Security Analysis Tools

### Slither (Static Analysis)

```bash
# Install via pip
pip3 install slither-analyzer

# Verify installation
slither --version

# Install solc-select for Solidity version management
pip3 install solc-select

# Install and use specific Solidity version
solc-select install 0.8.19
solc-select use 0.8.19
```

### MythX

```bash
# Install MythX CLI
pip3 install mythx-cli

# Verify installation
mythx version

# Login to MythX (requires API key from mythx.io)
mythx login
```

### Mythril (Symbolic Execution)

```bash
# Install via pip
pip3 install mythril

# Verify installation
myth version
```

### Securify

```bash
# Clone repository
git clone https://github.com/eth-sri/securify2.git
cd securify2

# Install dependencies
pip3 install -r requirements.txt

# Build Docker image (recommended)
docker build -t securify .
```

### Manticore (Symbolic Execution)

```bash
# Install via pip
pip3 install manticore[native]

# Verify installation
manticore --version
```

### Echidna (Property-based Testing)

```bash
# Download latest release
wget https://github.com/crytic/echidna/releases/latest/download/echidna-2.2.1-Linux.tar.gz

# Extract
tar -xzf echidna-2.2.1-Linux.tar.gz

# Move to PATH
sudo mv echidna /usr/local/bin/

# Verify installation
echidna --version
```

### Oyente (Vulnerability Detection)

```bash
# Clone repository
git clone https://github.com/enzymefinance/oyente.git
cd oyente

# Install via Docker (recommended)
docker pull luongnguyen/oyente

# Or install from source
pip install oyente
```

## 3. Web3 Infrastructure

### Metamask

1. Install browser extension from https://metamask.io/
2. Set up wallet and seed phrase
3. Add custom networks:

```javascript
// Localhost/Ganache
Network Name: Localhost 8545
RPC URL: http://127.0.0.1:8545
Chain ID: 1337
Currency Symbol: ETH

// Hardhat
Network Name: Hardhat
RPC URL: http://127.0.0.1:8545
Chain ID: 31337
Currency Symbol: ETH
```

### Infura API Key

1. Sign up at https://infura.io/
2. Create new project
3. Copy Project ID
4. Set environment variable:

```bash
echo 'export INFURA_API_KEY="your-project-id"' >> ~/.bashrc
source ~/.bashrc
```

### Alchemy API Key

1. Sign up at https://www.alchemy.com/
2. Create app
3. Copy API key
4. Set environment variable:

```bash
echo 'export ALCHEMY_API_KEY="your-api-key"' >> ~/.bashrc
source ~/.bashrc
```

### ethers.js and web3.js

```bash
# ethers.js
npm install ethers

# web3.js
npm install web3
```

## 4. Advanced Security Tools

### Surya (Contract Visualization)

```bash
npm install -g surya

# Generate control flow graph
surya graph contracts/*.sol | dot -Tpng > output.png

# Describe contract
surya describe contracts/MyContract.sol
```

### Tenderly

```bash
# Install CLI
npm install -g @tenderly/cli

# Login
tenderly login

# Export contract
tenderly export init
```

### Foundry Fuzz Testing

Already included in Foundry installation. Create fuzz tests:

```solidity
// In your test file
function testFuzz_Transfer(uint256 amount) public {
    vm.assume(amount <= token.balanceOf(address(this)));
    token.transfer(user, amount);
    assertEq(token.balanceOf(user), amount);
}
```

### Huff (Low-level Development)

```bash
# Install Huff compiler
npm install -g huffc

# Verify installation
huffc --version
```

### Dapptools

```bash
# Install via Nix
curl -L https://nixos.org/nix/install | sh

# Install dapptools
nix-env -f https://github.com/dapphub/dapptools/tarball/master -iA dapp seth solc hevm ethsign
```

## 5. Data and Network Access

### Testnet Setup

#### Goerli Testnet

```bash
# Get test ETH from faucet
# https://goerlifaucet.com/

# Add to Metamask
Network Name: Goerli
RPC URL: https://goerli.infura.io/v3/YOUR-PROJECT-ID
Chain ID: 5
Currency Symbol: GoerliETH
Block Explorer: https://goerli.etherscan.io
```

#### Sepolia Testnet

```bash
# Get test ETH
# https://sepoliafaucet.com/

# Add to Metamask
Network Name: Sepolia
RPC URL: https://sepolia.infura.io/v3/YOUR-PROJECT-ID
Chain ID: 11155111
Currency Symbol: SepoliaETH
Block Explorer: https://sepolia.etherscan.io
```

### Local Blockchain Forks

```bash
# Foundry (Anvil)
anvil --fork-url https://eth-mainnet.g.alchemy.com/v2/YOUR-API-KEY

# Hardhat
npx hardhat node --fork https://eth-mainnet.g.alchemy.com/v2/YOUR-API-KEY

# Ganache
ganache --fork.url https://eth-mainnet.g.alchemy.com/v2/YOUR-API-KEY
```

### Etherscan API

```bash
# Sign up at https://etherscan.io/apis
# Get API key

echo 'export ETHERSCAN_API_KEY="your-api-key"' >> ~/.bashrc
source ~/.bashrc
```

## 6. Automation and Integration

### CI/CD with GitHub Actions

Create `.github/workflows/security.yml`:

```yaml
name: Security Audit

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm install
      
      - name: Install Slither
        run: pip3 install slither-analyzer
      
      - name: Run Slither
        run: slither . --json slither-report.json
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: slither-report
          path: slither-report.json
```

### Scripting for Repetitive Tasks

```bash
# Create audit script
cat > audit.sh << 'EOF'
#!/bin/bash

echo "Running comprehensive security audit..."

# Static analysis with Slither
echo "1. Running Slither..."
slither . --json slither.json

# Symbolic execution with Mythril
echo "2. Running Mythril..."
myth analyze contracts/*.sol --solv 0.8.19 -o mythril.json

# Property-based testing with Echidna
echo "3. Running Echidna..."
echidna . --contract TestContract --config echidna.yaml

# Generate report
echo "4. Generating report..."
python3 generate_report.py

echo "Audit complete! Check reports in ./audit-reports/"
EOF

chmod +x audit.sh
```

### Integration with Bug Bounty Platforms

```bash
# Install Immunefi CLI (if available)
npm install -g immunefi-cli

# Or manually export findings to platforms:
# - Immunefi: https://immunefi.com/
# - HackerOne: https://hackerone.com/
# - Code4rena: https://code4rena.com/
```

## 7. Complete Setup Verification

Create a verification script:

```bash
cat > verify_setup.sh << 'EOF'
#!/bin/bash

echo "Verifying Web3 Development Environment Setup..."

# Check Node.js
echo -n "Node.js: "
node --version || echo "MISSING"

# Check npm
echo -n "npm: "
npm --version || echo "MISSING"

# Check Truffle
echo -n "Truffle: "
truffle version 2>/dev/null | head -1 || echo "MISSING"

# Check Hardhat
echo -n "Hardhat: "
npx hardhat --version 2>/dev/null || echo "MISSING"

# Check Foundry
echo -n "Forge: "
forge --version || echo "MISSING"

# Check Anvil
echo -n "Anvil: "
anvil --version || echo "MISSING"

# Check Slither
echo -n "Slither: "
slither --version || echo "MISSING"

# Check Mythril
echo -n "Mythril: "
myth version 2>/dev/null || echo "MISSING"

# Check Echidna
echo -n "Echidna: "
echidna --version 2>/dev/null || echo "MISSING"

# Check Surya
echo -n "Surya: "
surya --version 2>/dev/null || echo "MISSING"

# Check environment variables
echo ""
echo "Environment Variables:"
echo "INFURA_API_KEY: ${INFURA_API_KEY:+SET}"
echo "ALCHEMY_API_KEY: ${ALCHEMY_API_KEY:+SET}"
echo "ETHERSCAN_API_KEY: ${ETHERSCAN_API_KEY:+SET}"

echo ""
echo "Setup verification complete!"
EOF

chmod +x verify_setup.sh
./verify_setup.sh
```

## 8. Recommended Project Structure

```
project/
├── contracts/
│   ├── interfaces/
│   ├── libraries/
│   └── tokens/
├── test/
│   ├── unit/
│   ├── integration/
│   └── fuzzing/
├── scripts/
│   ├── deploy/
│   └── audit/
├── audit/
│   ├── reports/
│   └── findings/
├── .github/
│   └── workflows/
├── foundry.toml
├── hardhat.config.js
├── package.json
└── README.md
```

## 9. Essential Configuration Files

### foundry.toml

```toml
[profile.default]
src = "contracts"
out = "out"
libs = ["lib"]
solc_version = "0.8.19"
optimizer = true
optimizer_runs = 200
via_ir = false

[fuzz]
runs = 256
max_test_rejects = 65536

[invariant]
runs = 256
depth = 15
fail_on_revert = false
```

### hardhat.config.js

```javascript
require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-etherscan");
require("hardhat-gas-reporter");
require("solidity-coverage");

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {
      chainId: 31337
    },
    localhost: {
      url: "http://127.0.0.1:8545"
    },
    goerli: {
      url: `https://goerli.infura.io/v3/${process.env.INFURA_API_KEY}`,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    }
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY
  },
  gasReporter: {
    enabled: true,
    currency: "USD"
  }
};
```

## 10. Quick Reference Commands

```bash
# Compile contracts
forge build              # Foundry
npx hardhat compile      # Hardhat
truffle compile          # Truffle

# Run tests
forge test               # Foundry
npx hardhat test         # Hardhat
truffle test             # Truffle

# Deploy
forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast
npx hardhat run scripts/deploy.js --network goerli

# Security analysis
slither .
myth analyze contracts/MyContract.sol
echidna . --contract MyContract

# Local node
anvil                    # Foundry
npx hardhat node         # Hardhat
ganache                  # Ganache

# Gas reporting
forge test --gas-report
npx hardhat test

# Coverage
forge coverage
npx hardhat coverage
```

## Troubleshooting

### Common Issues

1. **Solidity version mismatch**: Use solc-select to manage versions
2. **Node memory issues**: Increase with `export NODE_OPTIONS="--max-old-space-size=4096"`
3. **Permission errors**: Use `sudo` carefully or fix npm permissions
4. **Network connection**: Check RPC URLs and API keys
5. **Tool conflicts**: Ensure only one version of each tool is in PATH

### Getting Help

- Foundry Discord: https://discord.gg/foundry
- Hardhat Discord: https://discord.gg/hardhat
- Ethereum StackExchange: https://ethereum.stackexchange.com/
- Trail of Bits Slack: https://slack.empirehacking.nyc/

## Next Steps

1. Complete all installations above
2. Run verification script
3. Create a test project
4. Run a sample audit
5. Integrate with your workflow
6. Set up CI/CD pipeline
7. Join community forums

This setup provides a complete, unrestricted Web3 development and security auditing environment with access to all major tools and networks.
