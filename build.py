import os.path
import platform
import shutil

import PyInstaller.__main__


def main():
    import time
    t = time.perf_counter()
    PyInstaller.__main__.run([
        '-y',
        '--clean',
        'main.spec',

    ])
    rootPath = "./dist/putonghuaASR-CN/"
    shutil.copy('config.yaml', rootPath)
    shutil.copy('logging.config.yaml', rootPath)
    shutil.copy('asr-hotwords.txt', rootPath)
    shutil.copytree('assert', os.path.join(rootPath, "assert"))
    shutil.copytree('weights', os.path.join(rootPath, "weights"))

    if platform.system() == "Windows":
        shutil.copytree('win-install/', os.path.join(rootPath, ""), dirs_exist_ok=True)

    elif platform.system() == "Linux":
        shutil.copytree('linux-install/', os.path.join(rootPath, ""), dirs_exist_ok=True)

    print(f"恭喜你！编译完成！ 耗时:{time.perf_counter() - t}s")


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
