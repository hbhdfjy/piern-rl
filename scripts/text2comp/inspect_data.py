"""检查 Stage 2 Text-to-Computation 训练数据。"""

import json
from collections import Counter
import os

def main():
    data_path = "data/text2comp/training_data.jsonl"

    print("=" * 70)
    print("Stage 2 Text-to-Computation 训练数据检查")
    print("=" * 70)
    print()

    # 基本统计
    template_counts = Counter()
    text_lengths = []
    total = 0

    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            template_counts[data['template_id']] += 1
            text_lengths.append(len(data['text']))
            total += 1

    print(f"文件: {data_path}")
    print(f"总训练对数: {total}")
    print(f"文件大小: {os.path.getsize(data_path) / 1024 / 1024:.2f} MB")
    print()

    # 文本长度统计
    print("文本长度统计:")
    print(f"  最短: {min(text_lengths)} 字符")
    print(f"  最长: {max(text_lengths)} 字符")
    print(f"  平均: {sum(text_lengths) / len(text_lengths):.1f} 字符")
    print()

    # 模板分布
    print("模板使用分布 (前 10):")
    for template_id, count in template_counts.most_common(10):
        print(f"  {template_id}: {count} ({count/total*100:.1f}%)")
    print()

    # 示例数据
    print("数据示例:")
    print("-" * 70)
    with open(data_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            data = json.loads(line)
            print(f"\n样本 {i+1} (模板: {data['template_id']}):")
            print(f"  文本: {data['text'][:100]}...")
            print(f"  参数: hk={data['params']['hk']:.2f}, sy={data['params']['sy']:.3f}, "
                  f"pumping={data['params']['pumping']:.1f}, strt={data['params']['strt']:.2f}, "
                  f"rch={data['params']['rch']:.4f}")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
