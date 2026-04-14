#!/bin/bash
# Se ejecuta antes de cualquier comando bash que Claude intente correr.
# Bloquea git commit/push si hay archivos sensibles en staging.

INPUT="$1"

# Solo actuar si el comando es git commit o git push
if ! echo "$INPUT" | grep -qE '(git commit|git push)'; then
  exit 0
fi

# Comprobar si .env u otros archivos sensibles están en staging
SENSITIVE=$(git diff --cached --name-only 2>/dev/null | grep -E '\.(env|key|pem|secret)$|credentials')

if [ -n "$SENSITIVE" ]; then
  echo "BLOQUEADO: Intentando commitear archivos sensibles:"
  echo "$SENSITIVE"
  exit 1
fi

exit 0