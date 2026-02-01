import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import os


class ActivityLogger:
    """Логирование активности с HTML-отчетами"""
    
    CATEGORIES = ["auth", "gifts", "automation", "manual", "api"]
    
    def __init__(self, log_dir: Optional[str] = None) -> None:
        if log_dir is None:
            # Определяем правильный путь от текущей директории
            current_dir = Path(__file__).parent.parent.parent
            log_dir = str(current_dir / "logs")
        
        self.log_dir = Path(log_dir)
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Не удалось создать директорию логов: {e}")
            # Используем /tmp для Linux
            self.log_dir = Path("/tmp") / "telegram_gift_logs"
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_activity(
        self,
        user_id: str,
        category: str,
        action: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирует активность"""
        if category not in self.CATEGORIES:
            category = "api"
        
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "category": category,
            "action": action,
            "status": status,
            "details": details or {}
        }
        
        # Сохраняем в файл
        log_file = self.log_dir / f"{category}_log.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def generate_html_report(self, category: Optional[str] = None) -> str:
        """Генерирует HTML-отчет"""
        logs = self._read_logs(category)
        
        html = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Отчет активности</title>
            <style>
                body {
                    font-family: 'Inter', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    overflow: hidden;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }
                .header h1 { margin: 0; font-size: 28px; }
                .header p { margin: 10px 0 0 0; opacity: 0.9; }
                .content {
                    padding: 30px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                thead {
                    background: #f5f5f5;
                    border-bottom: 2px solid #667eea;
                }
                th {
                    padding: 15px;
                    text-align: left;
                    font-weight: 600;
                    color: #333;
                }
                td {
                    padding: 12px 15px;
                    border-bottom: 1px solid #eee;
                }
                tr:hover { background: #f9f9f9; }
                .badge {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                }
                .badge-success { background: #10b981; color: white; }
                .badge-error { background: #ef4444; color: white; }
                .badge-pending { background: #f59e0b; color: white; }
                .badge-auth { background: #3b82f6; color: white; }
                .badge-gifts { background: #ec4899; color: white; }
                .badge-automation { background: #8b5cf6; color: white; }
                .stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .stat-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }
                .stat-card h3 { margin: 0 0 10px 0; }
                .stat-card .number { font-size: 32px; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Отчет активности</h1>
                    <p>Автоматический отчет системы управления подарками</p>
                    <p style="font-size: 12px;">{}</p>
                </div>
                <div class="content">
                    <div class="stats">
                        <div class="stat-card">
                            <h3>Всего операций</h3>
                            <div class="number">{}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Успешных</h3>
                            <div class="number">{}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Ошибок</h3>
                            <div class="number">{}</div>
                        </div>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Время</th>
                                <th>Пользователь</th>
                                <th>Категория</th>
                                <th>Действие</th>
                                <th>Статус</th>
                                <th>Детали</th>
                            </tr>
                        </thead>
                        <tbody>
                            {}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Формируем таблицу
        rows = []
        success_count = 0
        error_count = 0
        
        for log in logs:
            status = log.get("status", "unknown")
            if status == "success":
                success_count += 1
            elif status == "error":
                error_count += 1
            
            rows.append(f"""
            <tr>
                <td>{log.get('timestamp', 'N/A')[:19]}</td>
                <td>{log.get('user_id', 'N/A')}</td>
                <td><span class="badge badge-{log.get('category', 'api')}">{log.get('category', 'API')}</span></td>
                <td>{log.get('action', 'N/A')}</td>
                <td><span class="badge badge-{status}">{status.upper()}</span></td>
                <td><small>{json.dumps(log.get('details', {}))}</small></td>
            </tr>
            """)
        
        return html.format(
            datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S"),
            len(logs),
            success_count,
            error_count,
            "".join(rows)
        )
    
    def _read_logs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Читает логи из файлов (защищенный метод)"""
        logs: List[Dict[str, Any]] = []
        
        if category:
            files = [self.log_dir / f"{category}_log.jsonl"]
        else:
            files = list(self.log_dir.glob("*_log.jsonl"))
        
        for file in files:
            if file.exists():
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            logs.append(json.loads(line))
                        except Exception:
                            pass
        
        # Сортируем по времени (новые первыми)
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return logs[:1000]  # Последние 1000 записей
    
    def read_logs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Читает логи из файлов (публичный метод)"""
        return self._read_logs(category)
