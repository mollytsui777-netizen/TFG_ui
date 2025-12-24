#!/usr/bin/env bash
set -e

# 改进的统一评测脚本：基于官方 eval_all.py，自动处理环境切换
# 使用方法：
#   bash run_eval.sh --pred-video /path/to/pred.mp4 --gt-video /path/to/gt.mp4 [--all]
#   bash run_eval.sh --pred-video /path/to/pred.mp4 --gt-video /path/to/gt.mp4 --frame --niqe --fid

# 解析参数（透传给 eval_all.py）
ARGS="$@"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVAL_SCRIPT="$PROJECT_ROOT/TalkingGaussian/scripts/eval_all.py"

# 检查 eval_all.py 是否存在
if [ ! -f "$EVAL_SCRIPT" ]; then
  echo "错误: 未找到 eval_all.py: $EVAL_SCRIPT"
  exit 1
fi

echo "=========================================="
echo "TalkingGaussian 统一评测脚本（基于官方 eval_all.py）"
echo "=========================================="
echo ""

# 检查 conda 是否可用
if ! command -v conda &> /dev/null; then
  echo "错误: conda 未找到，请确保 conda 已安装并初始化"
  exit 1
fi

# 初始化 conda（如果需要）
if [ -f /opt/conda/etc/profile.d/conda.sh ]; then
  source /opt/conda/etc/profile.d/conda.sh
elif [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
  source ~/miniconda3/etc/profile.d/conda.sh
elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
  source ~/anaconda3/etc/profile.d/conda.sh
fi

# 检查 talking_gaussian 环境是否存在
if ! conda env list | grep -q "talking_gaussian"; then
  echo "错误: conda 环境 'talking_gaussian' 不存在"
  echo "请先创建环境: conda env create -f TalkingGaussian/environment.yml"
  exit 1
fi

# 运行评测（在 talking_gaussian 环境中）
echo "使用 conda 环境: talking_gaussian"
echo "运行命令: python $EVAL_SCRIPT $ARGS"
echo ""

conda run -n talking_gaussian --no-capture-output \
  python "$EVAL_SCRIPT" $ARGS

echo ""
echo "=========================================="
echo "评测完成！"
echo "=========================================="

