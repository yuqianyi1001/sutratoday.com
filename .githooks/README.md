# .githooks

这里的 16 个 hook 文件都是空的（只有一行 `#!/bin/sh`），故意保留。

用途：有的电脑上全局设置了 git hooks（例如 `~/.git-templates` 或全局 `core.hooksPath`），会在提交、推送时执行不需要的检查。在仓库里设置：

    git config core.hooksPath .githooks

之后 git 只运行这个目录里的空 hook，其他电脑上原有的 hooks 被覆盖，不再执行。

不要删除这些文件。要加检查（例如提交前跑 `scripts/check_frontmatter.py`），在对应文件里写命令即可。
