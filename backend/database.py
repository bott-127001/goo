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
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('risk_reward_ratio', '2.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('risk_percent', '1.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cooldown_minutes', '15')")
    # Add new Greek confirmation thresholds
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('confirm_delta_slope', '0.02')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('confirm_gamma_change', '8.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('confirm_iv_trend', '1.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('confirm_conditions_met', '2')")
    # Add new Market Type thresholds
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('atr_neutral_max', '10')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('atr_trendy_min', '10')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('atr_trendy_max', '18')")
    # Add new Continuation Entry thresholds
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cont_delta_thresh', '0.01')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cont_gamma_thresh', '3.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cont_iv_thresh', '0.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cont_theta_thresh', '5.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cont_conditions_met', '2')")
    # Add new Reversal Entry thresholds
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rev_delta_flip_thresh', '0.02')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rev_gamma_drop_thresh', '-5.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rev_iv_drop_thresh', '-1.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rev_conditions_met', '2')")
    # Add new Greek Exit thresholds
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('exit_delta_flip_thresh', '0.02')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('exit_gamma_drop_thresh', '-5.0')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('exit_iv_crush_thresh', '-1.5')")
    # Add new Time-Based Exit threshold
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('eod_exit_minutes', '60')")
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