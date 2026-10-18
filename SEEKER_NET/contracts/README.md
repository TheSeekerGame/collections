# contracts

The two SEEKER NET contracts. See "The contracts" in the main README.

- `src/`: the source files the deployed contracts were compiled from
- `flattened/`: each contract in one file, with all the library code it uses
- `abi/`: the ABI of each contract

Some comments in these files are worded slightly differently from the deployed source; comments are not part of the compiled code, and these files compile to exactly the deployed code (Solidity 0.8.17, optimizer 200 runs, EVM cancun, no metadata hash).
