import sqlite3
import datetime

DATABASE_FILE = "trading_log.db"

def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the trade_logs table if it doesn't exist."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trade_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            signal_type TEXT,
            status TEXT,
            strike_price REAL,
            entry_price REAL,
            exit_price REAL,
            result TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Insert default settings if they don't exist
    # --- Core Trade Management Settings ---
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('risk_reward_ratio', '2.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('risk_percent', '1.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cooldown_minutes', '15')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('eod_exit_minutes', '60')")

    # --- New Strategy Settings ---
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('market_type_window_size', '3')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bos_buffer_points', '10')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('retest_min_percent', '30')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('retest_max_percent', '60')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('entry_delta_slope_thresh', '0.01')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('entry_gamma_change_thresh', '5.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('entry_iv_trend_thresh', '0.5')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('entry_theta_max_spike', '5.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('exit_iv_crush_thresh', '-2.0')")

    conn.commit()
    conn.close()
    print("Database initialized.")

def log_signal(signal_data):
    """Logs a new signal to the database."""
    if not signal_data:
        return

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO trade_logs (timestamp, signal_type, status, strike_price) VALUES (?, ?, ?, ?)',
        (
            datetime.datetime.now().isoformat(),
            signal_data.get('type'),
            signal_data.get('status'),
            signal_data.get('strike_price')
        )
    )
    conn.commit()
    conn.close()
    log_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    print(f"Logged new signal (ID: {log_id}): {signal_data.get('type')} - {signal_data.get('status')}")
    return log_id

def update_log_entry(log_id, updates):
    """Updates an existing log entry with new data (e.g., status, entry_price, sl, target)."""
    if not log_id or not updates:
        return

    conn = get_db_connection()
    # Dynamically build the SET part of the SQL query
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values()) + [log_id]

    query = f"UPDATE trade_logs SET {set_clause} WHERE id = ?"
    conn.execute(query, values)
    conn.commit()
    conn.close()
    print(f"Updated log ID {log_id} with: {updates}")

def get_all_logs():
    """Retrieves all logs from the database, ordered by most recent first."""
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM trade_logs ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(log) for log in logs]

def get_settings():
    """Retrieves all settings from the database."""
    conn = get_db_connection()
    settings_cursor = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    # Convert list of rows to a dictionary
    return {row['key']: row['value'] for row in settings_cursor}

def update_setting(key, value):
    """Updates a specific setting in the database."""
    conn = get_db_connection()
    conn.execute(
        'UPDATE settings SET value = ? WHERE key = ?',
        (value, key)
    )
    conn.commit()
    conn.close()
    print(f"Updated setting: {key} = {value}")