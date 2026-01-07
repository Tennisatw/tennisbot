实现语音（可以先从tts和语音转文字开始）

<br>

接受文件，图片输入。暂没想好怎么处理。

<br>

简化一下前后端的逻辑

前提是我自己得看得懂代码。过两天再说吧。

<br>

后端 run_lock 是全局锁，会把所有 session 串行化。建议改成 “每个 session 一把锁”

<br>

edit_apply 工具的re有点问题，建议直接禁止。

<br>

archive_session 建议新开一个线程跑总结，以加速

<br>

补充test