# voice-proto

实时语音对话的最小原型。一轮对话从转写开始，模型按字返回，切成小段后合成并播放。新的一轮会取消还在播放的旧回复。

第 1 步用假的转写、假的模型和假的播放器把这条链路跑通：第一小段在模型说完之前就开始合成，新的一轮会丢掉上一轮还没播出的音频，每一轮把听、想、说和合计时间追加到日志。还没有麦克风，也没有真实接口。

规范见 [docs/提交规范.md](docs/提交规范.md)。

```shell
python -m pip install -r requirements-dev.txt
python main.py
pytest -q
```

`python main.py` 会跑一轮假对话，在终端打印计时，并把同一条记录追加到 `runs/turns.jsonl`。这个目录不提交。

推送到 GitHub 时，「提交检查」会把这次推送中的每一条提交单独检出并运行测试。
