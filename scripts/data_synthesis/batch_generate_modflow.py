"""
批量运行多个 MODFLOW 配置生成数据。

支持：
- 串行运行（安全，便于调试）
- 并行运行（快速，利用多核）
- 断点续传（跳过已生成的文件）
"""

import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict
import yaml
import os


class BatchMODFLOWGenerator:
    """批量 MODFLOW 数据生成器。"""

    def __init__(self, config_dir: str = "configs/data_synthesis/modflow_variants"):
        self.config_dir = Path(config_dir)
        self.modflow_bin = os.path.expanduser("~/bin/mf2005")

    def get_all_configs(self) -> List[Path]:
        """获取所有配置文件。"""
        configs = list(self.config_dir.glob("*.yaml"))
        # 排除 README
        configs = [c for c in configs if c.stem != "README"]
        return sorted(configs)

    def check_if_generated(self, config_path: Path) -> bool:
        """检查数据是否已生成。"""
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        output_file = Path(config["output_dir"]) / config["output_file"]
        return output_file.exists()

    def run_single_config(
        self, config_path: Path, skip_existing: bool = True
    ) -> Dict[str, any]:
        """运行单个配置。"""

        result = {
            "config": config_path.name,
            "success": False,
            "message": "",
            "duration": 0.0,
        }

        # 检查是否已生成
        if skip_existing and self.check_if_generated(config_path):
            result["success"] = True
            result["message"] = "已存在，跳过"
            return result

        print(f"\n{'='*70}")
        print(f"运行配置: {config_path.name}")
        print(f"{'='*70}")

        start_time = time.time()

        try:
            # 运行管线
            cmd = [
                "python",
                "-m",
                "data_synthesis.pipeline.modflow_pipeline",
                "--config",
                str(config_path),
            ]

            # 设置环境变量（添加 MODFLOW 路径）
            env = os.environ.copy()
            env["PATH"] = f"{os.path.dirname(self.modflow_bin)}:{env.get('PATH', '')}"

            process = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 小时超时
            )

            duration = time.time() - start_time

            if process.returncode == 0:
                result["success"] = True
                result["message"] = "成功"
                result["duration"] = duration
                print(f"\n✓ 成功！耗时: {duration:.1f}s")
            else:
                result["message"] = f"失败: {process.stderr[:200]}"
                print(f"\n✗ 失败！")
                print(f"错误: {process.stderr[:500]}")

        except subprocess.TimeoutExpired:
            result["message"] = "超时（>1小时）"
            print(f"\n✗ 超时！")

        except Exception as e:
            result["message"] = f"异常: {str(e)}"
            print(f"\n✗ 异常: {e}")

        return result

    def run_all_configs(
        self,
        skip_existing: bool = True,
        parallel: bool = False,
        max_workers: int = 4,
    ) -> List[Dict]:
        """运行所有配置。"""

        configs = self.get_all_configs()
        print(f"发现 {len(configs)} 个配置文件")
        print()

        if parallel:
            return self._run_parallel(configs, skip_existing, max_workers)
        else:
            return self._run_sequential(configs, skip_existing)

    def _run_sequential(
        self, configs: List[Path], skip_existing: bool
    ) -> List[Dict]:
        """串行运行。"""
        results = []

        for i, config in enumerate(configs, 1):
            print(f"\n[{i}/{len(configs)}] 处理: {config.name}")

            result = self.run_single_config(config, skip_existing)
            results.append(result)

            # 简要进度
            success_count = sum(1 for r in results if r["success"])
            print(f"\n当前进度: {success_count}/{i} 成功")

        return results

    def _run_parallel(
        self, configs: List[Path], skip_existing: bool, max_workers: int
    ) -> List[Dict]:
        """并行运行（使用 multiprocessing）。"""
        from concurrent.futures import ProcessPoolExecutor, as_completed

        print(f"使用 {max_workers} 个并行进程")
        print()

        results = []

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_config = {
                executor.submit(self.run_single_config, config, skip_existing): config
                for config in configs
            }

            # 收集结果
            for i, future in enumerate(as_completed(future_to_config), 1):
                config = future_to_config[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"\n[{i}/{len(configs)}] {config.name}: {result['message']}")
                except Exception as e:
                    print(f"\n[{i}/{len(configs)}] {config.name}: 异常 {e}")
                    results.append({
                        "config": config.name,
                        "success": False,
                        "message": f"异常: {e}",
                        "duration": 0.0,
                    })

        return results

    def print_summary(self, results: List[Dict]):
        """打印汇总报告。"""
        print()
        print("=" * 70)
        print("批量生成汇总")
        print("=" * 70)
        print()

        success = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        print(f"总配置数: {len(results)}")
        print(f"成功: {len(success)}")
        print(f"失败: {len(failed)}")
        print()

        if success:
            total_time = sum(r["duration"] for r in success)
            avg_time = total_time / len(success)
            print(f"总耗时: {total_time:.1f}s ({total_time/60:.1f}分钟)")
            print(f"平均耗时: {avg_time:.1f}s/配置")
            print()

        if failed:
            print("失败的配置:")
            for r in failed:
                print(f"  ✗ {r['config']}: {r['message']}")
            print()

        # 统计生成的样本数
        total_samples = 0
        for r in success:
            config_path = self.config_dir / r["config"]
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                total_samples += config["n_samples"]

        print(f"成功生成样本数: {total_samples}")
        print()

        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="批量运行 MODFLOW 数据生成")
    parser.add_argument(
        "--config-dir",
        type=str,
        default="configs/data_synthesis/modflow_variants",
        help="配置文件目录",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="跳过已生成的文件",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="重新生成所有文件",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="并行运行（实验性）",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="并行进程数",
    )
    parser.add_argument(
        "--single",
        type=str,
        help="只运行单个配置（文件名，如 baseline.yaml）",
    )

    args = parser.parse_args()

    generator = BatchMODFLOWGenerator(args.config_dir)

    if args.single:
        # 单个配置
        config_path = generator.config_dir / args.single
        if not config_path.exists():
            print(f"错误: 配置文件不存在: {config_path}")
            return

        result = generator.run_single_config(config_path, args.skip_existing)
        generator.print_summary([result])

    else:
        # 批量运行
        results = generator.run_all_configs(
            skip_existing=args.skip_existing,
            parallel=args.parallel,
            max_workers=args.max_workers,
        )
        generator.print_summary(results)


if __name__ == "__main__":
    main()
