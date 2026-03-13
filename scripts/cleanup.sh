#!/bin/bash
# 项目自动清理脚本

set -e

echo "======================================================================"
echo "项目清理"
echo "======================================================================"
echo ""

# 统计
deleted_count=0

# 1. 删除系统文件
echo "1. 删除系统临时文件..."
count=$(find . -name ".DS_Store" -type f | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
    find . -name ".DS_Store" -type f -delete
    echo "   ✓ 删除了 $count 个 .DS_Store 文件"
    deleted_count=$((deleted_count + count))
else
    echo "   - 没有找到 .DS_Store 文件"
fi

count=$(find . -name "*.tmp" -type f | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
    find . -name "*.tmp" -type f -delete
    echo "   ✓ 删除了 $count 个 .tmp 文件"
    deleted_count=$((deleted_count + count))
fi

count=$(find . -name "*.bak" -type f | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
    find . -name "*.bak" -type f -delete
    echo "   ✓ 删除了 $count 个 .bak 文件"
    deleted_count=$((deleted_count + count))
fi

count=$(find . -name "*~" -type f | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
    find . -name "*~" -type f -delete
    echo "   ✓ 删除了 $count 个 ~ 文件"
    deleted_count=$((deleted_count + count))
fi

# 2. 删除测试输出
echo ""
echo "2. 删除测试输出..."
if [ -d "data/text2comp/test" ]; then
    rm -rf data/text2comp/test/
    echo "   ✓ 删除了 data/text2comp/test/ 目录"
    deleted_count=$((deleted_count + 1))
else
    echo "   - 没有找到测试输出目录"
fi

# 3. 删除临时批次数据
echo ""
echo "3. 删除临时批次数据..."
count=0
for pattern in "*_batch_*.json" "*_progress.json" "*_test.jsonl" "*_old.*"; do
    files=$(find data/text2comp -name "$pattern" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$files" -gt 0 ]; then
        find data/text2comp -name "$pattern" -type f -delete
        count=$((count + files))
    fi
done
if [ "$count" -gt 0 ]; then
    echo "   ✓ 删除了 $count 个临时数据文件"
    deleted_count=$((deleted_count + count))
else
    echo "   - 没有找到临时数据文件"
fi

# 4. 删除 Python 缓存
echo ""
echo "4. 删除 Python 缓存..."
count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "   ✓ 删除了 $count 个 __pycache__ 目录"
    deleted_count=$((deleted_count + count))
fi

count=$(find . -name "*.pyc" -o -name "*.pyo" 2>/dev/null | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    echo "   ✓ 删除了 $count 个 .pyc/.pyo 文件"
    deleted_count=$((deleted_count + count))
fi

# 5. 删除日志文件
echo ""
echo "5. 删除临时日志文件..."
count=$(find . -name "*.log" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
    echo "   发现 $count 个 .log 文件"
    read -p "   是否删除？[y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        find . -name "*.log" -type f -delete
        echo "   ✓ 删除了 $count 个 .log 文件"
        deleted_count=$((deleted_count + count))
    else
        echo "   - 跳过日志文件"
    fi
else
    echo "   - 没有找到日志文件"
fi

# 总结
echo ""
echo "======================================================================"
echo "✓ 清理完成！"
echo "======================================================================"
echo ""
echo "总计删除: $deleted_count 个文件/目录"
echo ""
echo "建议："
echo "  - 查看 PROJECT_CLEANUP_CHECKLIST.md 了解清理原则"
echo "  - 定期运行此脚本保持项目整洁"
echo ""
echo "======================================================================"
