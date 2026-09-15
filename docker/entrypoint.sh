#!/bin/sh
set -e

# Fix ownership of data directories (volume may have been created by root)
chown -R orchard:orchard /data

# Drop to orchard user and exec the actual command
exec runuser -u orchard -- "$@"
