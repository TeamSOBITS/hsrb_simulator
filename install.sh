#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# HSRシミュレータ(新Gazebo / ROS 2 Jazzy)のセットアップスクリプト。
#
#   1. hsr-project の依存リポジトリ(jazzyブランチ)を src/ にclone
#   2. hsrb_description の重複を解決 (hsrb_common側を採用)
#   3. Jazzy / Gazebo Harmonic 対応パッチを適用 (patches/*.patch)
#   4. rosdepで依存をインストールし、hsrb_gazebo_bringup までビルド
#
# パッチの中身を変更したい場合は patches/ 以下の .patch を直接編集するか、
# 修正済みリポジトリで `git diff > patches/<repo>.patch` を実行して更新する。
# 全工程は冪等: 済んでいる工程はスキップされるため、何度実行してもよい。

set -Eeo pipefail

ROS_DISTRO_EXPECTED="jazzy"

# clone対象: "リポジトリ名 [sparse-checkoutパス]" (ブランチは全てjazzy)
CLONE_REPOS=(
  "tmc_drivers tmc_exxx_servo_motor_protocol"
  "tmc_realtime_control"
  "tmc_common"
  "tmc_common_msgs"
  "tmc_navigation"
  "tmc_gazebo"
  "hsrb_common"
  "hsrb_controllers"
)

# パッチ適用対象 (patches/<名前>.patch を src/<名前>/ に適用)
PATCH_REPOS=(
  "hsrb_simulator"
  "tmc_realtime_control"
  "tmc_navigation"
  "tmc_gazebo"
  "hsrb_controllers"
)

log()  { printf '\n\033[1;34m[hsrb-install]\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33m[warning]\033[0m %s\n' "$*" >&2; }
die()  { printf '\n\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

trap 'printf "\n\033[1;31m[error]\033[0m %s行目で失敗しました (exit %s)\n" \
      "${BASH_LINENO[0]:-?}" "$?" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname -- "$SCRIPT_DIR")"
WS_DIR="$(dirname -- "$SRC_DIR")"
PATCH_DIR="$SCRIPT_DIR/patches"

# ---------------------------------------------------------------- 環境確認
[[ -f "$SCRIPT_DIR/hsrb_gazebo_bringup/package.xml" ]] ||
  die "hsrb_simulatorのルートで実行してください"
[[ -f "/opt/ros/$ROS_DISTRO_EXPECTED/setup.bash" ]] ||
  die "ROS 2 ${ROS_DISTRO_EXPECTED} が見つかりません"

# ROSのsetup.bashは未定義変数を参照するため set -u は使わない
source "/opt/ros/$ROS_DISTRO_EXPECTED/setup.bash"

log "workspace: $WS_DIR"

# ---------------------------------------------------------------- clone
clone_repo() {
  local name="$1" sparse_path="${2:-}"
  local dir="$SRC_DIR/$name"
  local url="https://github.com/hsr-project/${name}.git"

  if [[ -d "$dir/.git" ]]; then
    log "$name: clone済み (スキップ)"
    return
  fi
  [[ ! -e "$dir" ]] || die "$dir が存在しますがgitリポジトリではありません"

  if [[ -n "$sparse_path" ]]; then
    log "$name: jazzyブランチをsparse clone ($sparse_path のみ)"
    git clone --filter=blob:none --sparse --branch jazzy "$url" "$dir"
    git -C "$dir" sparse-checkout set "$sparse_path"
  else
    log "$name: jazzyブランチをclone"
    git clone --branch jazzy --depth 1 "$url" "$dir"
  fi
}

for entry in "${CLONE_REPOS[@]}"; do
  # shellcheck disable=SC2086
  clone_repo $entry
done

# ------------------------------------------- hsrb_description の重複解決
# hsrb_common にも hsrb_description が同梱されているため、単独cloneが
# ある場合は COLCON_IGNORE で無効化して hsrb_common 側を使う。
if [[ -f "$SRC_DIR/hsrb_description/package.xml" ]] &&
   [[ -f "$SRC_DIR/hsrb_common/hsrb_description/package.xml" ]] &&
   [[ ! -f "$SRC_DIR/hsrb_description/COLCON_IGNORE" ]]; then
  log "hsrb_descriptionの重複: 単独版をCOLCON_IGNOREで無効化します"
  touch "$SRC_DIR/hsrb_description/COLCON_IGNORE"
fi

# ---------------------------------------------------------------- パッチ
# Jazzy / Gazebo Harmonic (gz sim 8) 対応の修正一式。内訳:
#   hsrb_simulator       gz vendor化・gz_ros2_control Jazzy API・
#                        コントローラ設定のtimeout調整
#   tmc_realtime_control 旧3引数init()のon_init()移行・chainable API
#   tmc_navigation       tf2/PCLヘッダ改名対応・重複env hook削除
#   tmc_gazebo           odometry_publisherのignition→gz移植
#   hsrb_controllers     control_msgsフィールド改名・Lifecycle API
apply_patch() {
  local name="$1"
  local dir="$SRC_DIR/$name"
  local patch="$PATCH_DIR/$name.patch"

  [[ -f "$patch" ]] || die "パッチがありません: $patch"
  [[ -d "$dir" ]] || die "リポジトリがありません: $dir"

  if git -C "$dir" apply --reverse --check "$patch" 2>/dev/null; then
    log "$name: パッチ適用済み (スキップ)"
  elif git -C "$dir" apply --check "$patch" 2>/dev/null; then
    log "$name: パッチを適用します"
    git -C "$dir" apply "$patch"
  else
    die "$name: パッチが現在のソースに合いません。上流の更新と競合している
可能性があります。リポジトリの状態 (git -C $dir status) を確認してください"
  fi
}

for name in "${PATCH_REPOS[@]}"; do
  apply_patch "$name"
done

# ---------------------------------------------------------------- rosdep
log "rosdepで依存パッケージをインストールします"
rosdep update
rosdep install \
  --from-paths \
    "$SCRIPT_DIR" \
    "$SRC_DIR/tmc_drivers/tmc_exxx_servo_motor_protocol" \
    "$SRC_DIR/tmc_realtime_control" \
    "$SRC_DIR/tmc_common" \
    "$SRC_DIR/tmc_common_msgs" \
    "$SRC_DIR/tmc_navigation" \
    "$SRC_DIR/tmc_gazebo" \
    "$SRC_DIR/hsrb_common" \
    "$SRC_DIR/hsrb_controllers" \
  --ignore-src --rosdistro "$ROS_DISTRO_EXPECTED" -r -y

# ---------------------------------------------------------------- build
log "hsrb_gazebo_bringupまでビルドします"
cd "$WS_DIR"
colcon build \
  --symlink-install \
  --packages-up-to hsrb_gazebo_bringup \
  --cmake-args -DBUILD_TESTING=OFF

source "$WS_DIR/install/setup.bash"

# ---------------------------------------------------------------- 確認
log "主要パッケージの生成を確認します"
for pkg in tmc_exxx_servo_motor_protocol tmc_realtime_controllers \
           tmc_gz_plugins hsrb_base_controllers hsrb_gripper_controller \
           hsrb_gz_ros2_control hsrb_gazebo_bringup; do
  ros2 pkg prefix "$pkg" > /dev/null || die "パッケージが見つかりません: $pkg"
  printf '  ✔ %s\n' "$pkg"
done

log "セットアップ完了。新しいターミナルでは次を実行してください:"
printf '  source %q\n\n' "$WS_DIR/install/setup.bash"
