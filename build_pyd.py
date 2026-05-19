import glob
import logging
import os

from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize

logging.basicConfig(level=logging.DEBUG)


class BuildPyd:
    def __init__(self, src_root, dirs, files):
        self.src_root = src_root
        self.dirs = [os.path.join(src_root, p) for p in dirs]
        self.files = [os.path.join(src_root, f) for f in files]
        self.pyFiles = []

    def exec_build_pyd(self):

        self.pyFiles += self.files
        for fs in self.dirs:
            self.pyFiles += self._find_files(fs)
        # for f in self.pyFiles:
        #     print(f)

        extensions = [
            Extension(
                file.replace("\\", ".").replace("/", ".").replace(".py", ""),  # 模块名称
                # os.path.basename(file),
                [f'{file}'],  # 模块路径
                # library_dirs=[os.path.dirname(file)]
            )
            for file in self.pyFiles
        ]
        packages = [file.replace("\\", ".").replace("/", ".").replace(".py", "") for file in self.pyFiles]

        # 每次打包前先删除旧产物，避免 build_ext 复用上一次的 pyd/c/html。
        self.clean_c_html()
        self.clean_pyd(strict=True)

        build_jobs = max(1, os.cpu_count())
        logging.info("开始生成 pyd，并发数: %s", build_jobs)

        setup(
            name="HS-ASR",
            version="1.0",
            ext_modules=cythonize(
                extensions,
                compiler_directives={'language_level': 3},
                annotate=True, force=True,
                nthreads=build_jobs,
            ),
            script_args=["build_ext", "--inplace", "--parallel", str(build_jobs)],  # "--inplace"
            src_root=self.src_root,
        )
        return packages

    def clean_c_html(self):
        for file in self.pyFiles:
            try:
                os.remove(file.replace(".py", ".c"))
                os.remove(file.replace(".py", ".html"))
                ...
            except:
                ...

    def clean_pyd(self, strict=False):
        suffixes = [
            ".cp310-win_amd64.pyd",
            ".cp38-win_amd64.pyd",
            ".cpython-310-loongarch64-linux-gnu.so",
            ".cpython-38-loongarch64-linux-gnu.so",
            ".cpython-310-aarch64-linux-gnu.so",
            ".cpython-38-aarch64-linux-gnu.so",
            ".cpython-310-x86_64-linux-gnu.so",
            ".cpython-38-x86_64-linux-gnu.so"
        ]

        for file in self.pyFiles:
            for suffix in suffixes:
                pyd_file = file.replace(".py", suffix)
                if os.path.exists(pyd_file):
                    try:
                        os.remove(pyd_file)
                        print(f"成功删除文件：{pyd_file}")
                    except Exception as e:
                        if strict:
                            raise PermissionError(
                                f"旧 pyd 文件被占用，无法重新生成，请先关闭正在运行的服务或 Python 进程: {pyd_file}"
                            ) from e
                        print(f"删除文件失败：{pyd_file}，原因：{e}")

    def _find_files(self, path):
        py_files = []  # 存储.py文件列表

        # 遍历文件夹及其子目录
        for foldername, subfolders, filenames in os.walk(path):
            if foldername.startswith(os.path.join('.', '.git')):
                continue
            if foldername.startswith(os.path.join('.', '.venv')):
                continue
            if foldername.startswith(os.path.join('.', 'venv')):
                continue
            if foldername.startswith(os.path.join('.', '.idea')):
                continue
            if foldername.startswith(os.path.join('.', 'build')):
                continue
            if foldername.startswith(os.path.join('.', 'dist')):
                continue
            if foldername.startswith(os.path.join('.', 'VAD')):
                continue
            if foldername.startswith(os.path.join('.', 'test_hs')):
                continue

            if foldername == '.':
                continue
            for filename in filenames:
                if filename.endswith('.py') and not filename.endswith('__init__.py'):
                    filepath = os.path.join(foldername, filename)
                    if filepath.startswith(".\\"):
                        filepath = filepath[2:]
                    if filepath.startswith("./"):
                        filepath = filepath[2:]
                    py_files.append(filepath)
        return py_files


if __name__ == '__main__':
    pydDirs = ['.']  # 编译 PYD 的文件夹
    pydFiles = []  # 编译 PYD 的文件
    build_pyd = BuildPyd('.', pydDirs, pydFiles)

    build_pyd.exec_build_pyd()
    build_pyd.clean_c_html()
    build_pyd.clean_pyd()
