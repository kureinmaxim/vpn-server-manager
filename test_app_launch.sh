#!/bin/bash
cd dist
echo "Запуск приложения..."
./VPNServerManager-Clean.app/Contents/MacOS/VPNServerManager-Clean > /tmp/vpn_app.log 2>&1 &
APP_PID=$!
echo "PID: $APP_PID"
sleep 3
if ps -p $APP_PID > /dev/null 2>&1; then
    echo "✅ Приложение работает"
    echo "Логи:"
    tail -20 /tmp/vpn_app.log
else
    echo "❌ Приложение завершилось"
    echo "Последние строки лога:"
    tail -50 /tmp/vpn_app.log | grep -A5 -B5 -E "Error|error|Exception|Traceback"
fi
