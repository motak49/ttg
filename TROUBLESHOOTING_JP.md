# TTG カメラ初期化エラーの解決方法

## エラー内容
```
ERROR: Cannot connect to device with name "5.2", it is used by another process.
Error: X_LINK_DEVICE_ALREADY_IN_USE
```

## 原因
depthai USB デバイスドライバが前のセッションのハンドルをキャッシュしている場合があります。

## 解決方法

### 方法 1: 簡易リセット（推奨）
1. **アプリケーションと全 Python プロセスを終了**
   - タスクマネージャーですべての `python.exe` プロセスを終了
   - または PowerShell で:
     ```powershell
     taskkill /IM python.exe /F
     ```

2. **USB デバイスを USB ポートから抜く**
   - USB ケーブルを OAK-D カメラから抜く
   - 10 秒以上待つ

3. **USB デバイスを再度接続**
   - USB ケーブルを USB ポートに戻す
   - 3 秒以上待つ

4. **アプリケーションを再起動**
   ```powershell
   cd d:\VSCode\ttg
   & '.\.venv\Scripts\python.exe' main.py
   ```

### 方法 2: デバイスドライバリセット（Windows）
1. デバイスマネージャーを開く (`devmgmt.msc`)
2. `Universal Serial Bus devices` を展開
3. OAK-D または Luxonis デバイスを右クリック
4. 「デバイスをアンインストール」を選択
5. 「このデバイスのドライバー ソフトウェアも削除します」にチェック
6. 再度 USB を接続すると自動的にドライバが再インストールされます

### 方法 3: 全リセット
1. すべてのプロセスを終了
2. 以下を実行:
   ```powershell
   cd d:\VSCode\ttg
   & '.\.venv\Scripts\python.exe' complete_reset.py
   ```
3. 5 秒待つ
4. `main.py` を実行

## トラブルシューティング

### まだエラーが出る場合
- PC を再起動してから再度試してください
- 別の USB ポートに接続してください
- 別のマシンで試してください（デバイスの故障確認）

### デバイスが見つからない場合
- USB ケーブルがしっかり接続されているか確認
- 別の USB ハブを試してください（直接 PC に接続）
- ドライバが正しくインストールされているか確認
  ```powershell
  & '.\.venv\Scripts\python.exe' -c "import depthai as dai; print([d.name for d in dai.Device.getAllAvailableDevices()])"
  ```
