#!/usr/bin/env bash
# 把本仓库的 dev-* skills 用软链接装到 Claude Code 和 Codex 的全局 skills 目录。
# 用法：
#   ./install.sh              安装（目标已有同名目录或指向别处的软链接时，先移到备份目录）
#   ./install.sh --uninstall  删除指向本仓库的软链接（不会自动恢复备份）
#   ./install.sh --status     查看安装情况
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TARGETS=()
[ -d "$HOME/.claude" ] && TARGETS+=("$HOME/.claude/skills")
[ -d "${CODEX_HOME:-$HOME/.codex}" ] && TARGETS+=("${CODEX_HOME:-$HOME/.codex}/skills")
BACKUP="$HOME/.cache/devflow-backup/$(date +%Y%m%d-%H%M%S)"

# 本仓库里所有带 SKILL.md 的 dev-* 目录，每行一个（支持路径里有空格）
# 只用 shell 通配符，macOS 自带的 bash 3.2 / BSD 工具也能用
list_skills() {
  local d
  for d in "$REPO"/dev-*/; do
    [ -f "${d}SKILL.md" ] && printf '%s\n' "${d%/}"
  done
  return 0
}

backup() { # $1=目标目录 $2=要移走的路径
  local sub; sub="$BACKUP/$(basename "$(dirname "$1")")"
  mkdir -p "$sub"
  mv "$2" "$sub/"
  echo "已备份 $2 → $sub/$(basename "$2")"
}

if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "没有找到 ~/.claude 或 ~/.codex，未安装。" >&2
  exit 1
fi

case "${1:-install}" in
  install)
    for t in "${TARGETS[@]}"; do
      mkdir -p "$t"
      while IFS= read -r s; do
        dest="$t/$(basename "$s")"
        if [ -L "$dest" ]; then
          if [ "$(readlink "$dest")" = "$s" ]; then continue; fi
          backup "$t" "$dest"            # 指向别处的软链接也先备份，不直接删
        elif [ -e "$dest" ]; then
          backup "$t" "$dest"
        fi
        ln -s "$s" "$dest"
      done < <(list_skills)
      # 清理指向本仓库、但目标已不存在的软链接（skill 被删除或改名）
      for l in "$t"/dev-*; do
        if [ -L "$l" ] && [ ! -e "$l" ]; then
          case "$(readlink "$l")" in "$REPO"/*) rm "$l"; echo "已清理失效链接 $l" ;; esac
        fi
      done
      echo "已安装到 $t"
    done
    if [ -d "$BACKUP" ]; then echo "旧版本备份在 $BACKUP（需要时可手动移回）"; fi
    ;;
  --uninstall)
    for t in "${TARGETS[@]}"; do
      while IFS= read -r s; do
        dest="$t/$(basename "$s")"
        if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$s" ]; then rm "$dest"; echo "已删除 $dest"; fi
      done < <(list_skills)
      for l in "$t"/dev-*; do   # 指向本仓库、但已失效的旧链接也删掉
        if [ -L "$l" ] && [ ! -e "$l" ]; then
          case "$(readlink "$l")" in "$REPO"/*) rm "$l"; echo "已删除失效链接 $l" ;; esac
        fi
      done
    done
    echo "备份目录 $HOME/.cache/devflow-backup/ 里的旧版本不会自动恢复。"
    ;;
  --status)
    echo "版本：$(cat "$REPO/VERSION" 2>/dev/null || echo 未知)"
    for t in "${TARGETS[@]}"; do
      echo "== $t"
      while IFS= read -r s; do
        name="$(basename "$s")"; dest="$t/$name"
        if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$s" ]; then echo "  ✓ $name"
        elif [ -e "$dest" ] || [ -L "$dest" ]; then echo "  ! $name（存在，但不是指向本仓库的软链接）"
        else echo "  ✗ $name（未安装）"; fi
      done < <(list_skills)
      for l in "$t"/dev-*; do
        if [ -L "$l" ] && [ ! -e "$l" ]; then echo "  ! $(basename "$l")（失效链接，运行 ./install.sh 会清理）"; fi
      done
    done
    ;;
  *) echo "未知参数：$1" >&2; exit 2 ;;
esac
