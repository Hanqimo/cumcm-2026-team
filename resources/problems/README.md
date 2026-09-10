# 历年国赛试题资料库（2021-2025）

本目录按 A-E 题分类，收录全国大学生数学建模竞赛官网的试题名称、简要主题说明、官方来源链接、下载工具和本地文件。

## 使用方式

`A/` 至 `E/` 保存分类索引，下载后的题面和附件统一放入 `library/<题号>/<年份>/`。下载和解压缓存放入 `.cache/`，该缓存不会进入 Git。

队员可运行以下命令，将官方压缩包下载并按 A-E 题整理到资料库。

```powershell
powershell -ExecutionPolicy Bypass -File .\resources\problems\download-official.ps1
```

如需在本地生成可检索的 Markdown 文本，可先安装 `pypdf`，再运行：

```powershell
python .\resources\problems\convert-local-pdfs.py
```

转换结果位于 `resources/problems/markdown/`。PDF 文本抽取可能丢失公式、图形或排版，阅读和复现时应以官方 PDF 为准。

## 分类入口

- [A 题](A/README.md)
- [B 题](B/README.md)
- [C 题](C/README.md)
- [D 题](D/README.md)
- [E 题](E/README.md)
- [优秀论文库与文件索引](../papers/README.md)

论文库可通过以下命令增量下载和维护：

```powershell
python .\resources\papers\fetch_library.py
```

`resources/papers/README.md` 与 `resources/papers/index.json` 保存文件索引、来源和核验状态。新增资料提交前应保留来源信息，并检查文件大小和重复项。

## 官方归档

- [历年竞赛赛题](https://www.mcm.edu.cn/html_cn/block/8579f5fce999cdc896f78bca5d4f8237.html)
- [2025 年赛题页面](https://www.mcm.edu.cn/html_cn/node/03c91a444e62eee81a3740fa97a461a6.html)
- [2024 年赛题页面](https://www.mcm.edu.cn/html_cn/node/a0c1fb5c31d43551f08cd8ad16870444.html)
- [2023 年赛题页面](https://www.mcm.edu.cn/html_cn/node/c74d72127066f510a5723a94b5323a26.html)
- [2022 年赛题页面](https://www.mcm.edu.cn/html_cn/node/388239ded4b057d37b7b8e51e33fe903.html)
- [2021 年赛题页面](https://www.mcm.edu.cn/html_cn/node/90d223833c1eb50f899aa096a66c6896.html)
