#!/usr/bin/env bash
# scripts/gen_grpc.sh — regenerate Python gRPC stubs from .proto files.
set -euo pipefail
OUT=src/qaforge/api/grpc/generated
mkdir -p "$OUT"
python -m grpc_tools.protoc -I proto \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  proto/*.proto
# Patch imports — protoc generates absolute imports that don't work for our package.
for f in "$OUT"/*_pb2_grpc.py; do
  sed -i.bak -E 's/^import ([a-zA-Z_]+_pb2)/from . import \1/' "$f" && rm "${f}.bak"
done
echo "Stubs regenerated in $OUT"
