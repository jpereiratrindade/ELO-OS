#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Development launcher with local camera preview; never installs a service.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONTAINER=${ELO_AV_CONTAINER:-elo-os}
MODELS=${ELO_VISION_MODEL_DIR:-$ROOT/../elo/build/models}
args=("$@")
has_option() {
  local option=$1 argument
  shift
  for argument in "$@"; do
    if [[ "$argument" == "$option" || "$argument" == "$option="* ]]; then return 0; fi
  done
  return 1
}
if ! has_option --camera "${args[@]}"; then
  case ${ELO_CAMERA:-/dev/video0} in
    off|none|0) ;;
    *)
      if [[ -f "$MODELS/face_detection_yunet_2023mar.onnx" ]]; then
        args+=(--camera "${ELO_CAMERA:-/dev/video0}")
      else
        echo "ELO: detector ausente em $MODELS; câmera desativada. Defina ELO_VISION_MODEL_DIR." >&2
      fi
      ;;
  esac
fi
if has_option --camera "${args[@]}"; then
  if ! has_option --detector-model "${args[@]}"; then args+=(--detector-model "$MODELS/face_detection_yunet_2023mar.onnx"); fi
  if ! has_option --recognizer-model "${args[@]}" && [[ -f "$MODELS/face_recognition_sface_2021dec_int8.onnx" ]]; then
    args+=(--recognizer-model "$MODELS/face_recognition_sface_2021dec_int8.onnx")
  fi
  if has_option --recognizer-model "${args[@]}"; then
    if ! has_option --recognition-store "${args[@]}"; then args+=(--recognition-store "$HOME/.local/share/elo-client/private/visits.json"); fi
  fi
fi
exec toolbox run -c "$CONTAINER" env \
  ELO_ENABLE_MULTIMEDIA=ON ELO_ENABLE_VISION=ON \
  CLIENT_BUILD_DIR="$ROOT/build/client-av" \
  "$ROOT/scripts/run-thin-client.sh" "${args[@]}"
