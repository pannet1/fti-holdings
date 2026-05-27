# TrackHoldings — Holdings Management Feature

## Overview

Manages paper entries holdings files that record open positions.  
The file path depends on the `paper` flag in the global settings (`O_SETG["paper"]`):
Logic is that we dont want to accidently mess with real trades taken.

- **Live mode** (`paper: 0`): `data/holdings.csv`  
- **Paper mode** (`paper: 1`): `data/paper/holdings.csv`

The feature provides read and write operations that are consumed by strategies such as Ratchet.  
No business logic lives in the feature – it is a pure I/O adapter.

## File Naming

The base directory is determined by the `paper` setting:

| `paper` value | Base path               |
|---------------|-------------------------|
| `0` (live)    | `data/`                 |
| `1` (paper)   | `data/paper/`           |

The directory for paper mode is automatically created on the first write if it does not exist.

## CSV Schema

```
datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy
```
