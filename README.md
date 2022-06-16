# prune-merged-branches

Script to clean up your local Git checkout by removing local branches whose
changes have been integrated into the main development branch.

When this script is run it will:

1. Determine the main development branch
2. Remove any branches which have been explicitly merged into the main branch
3. Check for local branches which would produce no changes if merged into the
   main branch, and offer to remove them
4. Check for local branches which track remote branches that have been removed,
   and offer to remove them

## Requirements

This script requires Python 3.8 or later.

## Usage

1. Clone this repository
2. `cd` into the target Git repository that you want to clean up
3. Check out the main development branch in the target repo and run `git pull`
   to ensure it is up to date with the remote side (eg. on GitHub)
4. Run the `prune-merged-branches.py` script from this repository
