# 接入现有浏览器录制

先检查项目当前的 Playwright 版本、fixture 和输出目录，复用已有用例与断言。应用部署在哪台机器、浏览器运行在哪台机器、视频最终保存在哪台机器是三个不同信息，不按服务地址推断录像位置。

## Playwright

- 已有 Playwright Test 用例：对本次演示场景启用 `video: 'on'`，保留成功用例的视频；`retain-on-failure` 会删除成功录像。范围限制在演示运行，不为交付录屏长期打开全库录像。
- 已有脚本：创建专用 context 时加 `recordVideo`，视口和录像尺寸保持一致以便看清文字。非登录场景先在不录像的步骤完成测试账号登录，再复用登录状态；登录场景按主 skill 遮蔽秘密，认证文件不提交或上传。
- 直接调库的生命周期示例（并入项目已有脚本，不是独立框架）：

  ```js
  const context = await browser.newContext({
    ...existingContextOptions,
    viewport: { width: 1440, height: 960 },
    recordVideo: { dir: evidenceDir, size: { width: 1440, height: 960 } },
  });
  const page = await context.newPage();
  const video = page.video();
  try {
    await runExistingScenario(page); // 保留页面/接口断言；失败照常抛出
  } finally {
    await context.close(); // 先关闭，等待录像写完
    if (video) await video.saveAs(outputWebm);
  }
  ```

  `existingContextOptions`、路径和场景来自项目；浏览器由原入口负责释放。多页面会产生多个视频，只收集实际覆盖场景的页面。原场景失败时即使保存了录像，也不能报告成功。

- CDP/远程浏览器不保证支持同一套录制 API；先看现有入口是否支持录像导出。支持时用其导出方法或 `video.saveAs()` 获取文件；不要把远程路径当本机文件，`video.path()` 在远程连接时会抛错。无录像能力时按主 skill 的截图方式交付，不为录屏开放调试端口或建立新的云会话。

官方参考：[录制视频](https://playwright.dev/docs/videos)、[Video API](https://playwright.dev/docs/api/class-video)。

## 成片与播放

原始 WebM 已能播放时可以直接交付。需要 MP4 兼容性时，用本机已有 FFmpeg 转码；字幕、裁空白和点击提示都可选，不要求安装额外工具。示例（路径来自本次产物目录）：

```bash
ffmpeg -i input.webm -c:v libx264 -pix_fmt yuv420p -movflags +faststart -an output.mp4
```

这个命令不覆盖原始文件、不剪掉步骤，并移除音轨；场景需要音频时不要使用 `-an`。实际播放成片并检查开头、关键结果与结尾，上传后再核对预览页面能播放和跳转；编码成功或 HTTP 200 不能替代播放检查。

字幕只陈述已经断言的结果。使用模拟上游时可写“保存校验与刷新回读通过；未验证真实上游调用”，不要改写成“全流程通过”。
