# voice-proto

实时语音对话的最小原型。一轮对话从转写开始，模型按字返回，切成小段后合成并播放。新的一轮会取消还在播放的旧回复。

原型代码还没开始。当前仓库先固定提交规范：导师按提交记录打分，所以每一次提交都要独立可测。

规范见 [docs/提交规范.md](docs/提交规范.md)。

```shell
python -m pip install -r requirements-dev.txt
pytest -q
```

推送到 GitHub 时，「提交检查」会把这次推送中的每一条提交单独检出并运行测试。
