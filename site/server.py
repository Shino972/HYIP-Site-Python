import asyncio
import aiosqlite
import aiohttp
from aiohttp import web
import hashlib
import time
import json
import os

SHOP_ID = '580'
SHOP_TOKEN = 'x-6082e15b78a82139df1e54b77ab61d78'

async def init_db():
    async with aiosqlite.connect('users.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            balance REAL DEFAULT 0.0,
            referrer_id INTEGER,
            is_admin INTEGER DEFAULT 0,
            FOREIGN KEY(referrer_id) REFERENCES users(id)
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER,
            session_token TEXT,
            expiry INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            start_time INTEGER,
            expiry INTEGER,
            created_at INTEGER,
            card_type TEXT,
            profitability REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            unique_id TEXT,
            amount REAL,
            status TEXT,
            type TEXT,
            created_at INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER,
            FOREIGN KEY(referrer_id) REFERENCES users(id),
            FOREIGN KEY(referred_id) REFERENCES users(id)
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            payeer_account TEXT,
            status TEXT,
            created_at INTEGER,
            updated_at INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        admin_email = 'admin@gmail.com'
        admin_password = hash_password('garden514')
        cursor = await db.execute('SELECT id FROM users WHERE email = ?', (admin_email,))
        admin_exists = await cursor.fetchone()
        if not admin_exists:
            await db.execute('INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)',
                            (admin_email, admin_password, 1))
        await db.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

async def register(request):
    data = await request.json()
    email = data.get('email')
    password = data.get('password')
    ref_id = data.get('ref_id')

    async with aiosqlite.connect('users.db') as db:
        try:
            await db.execute('INSERT INTO users (email, password, balance, referrer_id) VALUES (?, ?, ?, ?)',
                           (email, hash_password(password), 0.0, ref_id))
            await db.commit()
            user_id = await (await db.execute('SELECT id FROM users WHERE email = ?', (email,))).fetchone()
            if ref_id:
                await db.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)',
                               (ref_id, user_id[0]))
            session_token = hashlib.sha256(str(time.time()).encode()).hexdigest()
            expiry = int(time.time()) + 24 * 3600
            await db.execute('INSERT INTO sessions (user_id, session_token, expiry) VALUES (?, ?, ?)',
                           (user_id[0], session_token, expiry))
            await db.commit()
            response = web.json_response({'success': True})
            response.set_cookie('session_token', session_token, max_age=24*3600)
            return response
        except aiosqlite.IntegrityError:
            return web.json_response({'success': False, 'message': 'Email уже зарегистрирован'}, status=400)

async def login(request):
    data = await request.json()
    email = data.get('email')
    password = data.get('password')

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT id, password, is_admin FROM users WHERE email = ?', (email,))
        user = await cursor.fetchone()
        if user and user[1] == hash_password(password):
            session_token = hashlib.sha256(str(time.time()).encode()).hexdigest()
            expiry = int(time.time()) + 24 * 3600
            await db.execute('INSERT INTO sessions (user_id, session_token, expiry) VALUES (?, ?, ?)',
                           (user[0], session_token, expiry))
            await db.commit()
            response = web.json_response({'success': True, 'is_admin': user[2]})
            response.set_cookie('session_token', session_token, max_age=24*3600)
            return response
        return web.json_response({'success': False, 'message': 'Неверный email или пароль'}, status=401)

async def check_session(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False}, status=401)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id, expiry FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if session:
            cursor = await db.execute('SELECT id, balance, is_admin FROM users WHERE id = ?', (session[0],))
            user = await cursor.fetchone()
            cursor = await db.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (session[0],))
            referral_count = (await cursor.fetchone())[0]
            return web.json_response({
                'success': True,
                'user_id': user[0],
                'balance': user[1],
                'referral_count': referral_count,
                'is_admin': user[2]
            })
        return web.json_response({'success': False}, status=401)

async def logout(request):
    session_token = request.cookies.get('session_token')
    async with aiosqlite.connect('users.db') as db:
        await db.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
        await db.commit()
    response = web.json_response({'success': True})
    response.del_cookie('session_token')
    return response

async def rent_card(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    data = await request.json()
    amount = data.get('amount')
    card_type = data.get('card_type', 'gtx1060')

    # Параметры для разных карт
    card_params = {
        'gtx1060': {
            'min_amount': 100,
            'max_amount': 150,
            'profitability': 1.02,  # 102%
            'duration': 24 * 3600  # 24 часа
        },
        'rtx4090': {
            'min_amount': 1000,
            'max_amount': 5000,
            'profitability': 1.30,  # 130%
            'duration': 72 * 3600  # 72 часа
        },
        'rx580': {
            'min_amount': 500,
            'max_amount': 1000,
            'profitability': 1.10,  # 110%
            'duration': 48 * 3600  # 48 часов
        }
    }

    params = card_params.get(card_type, card_params['gtx1060'])
    if amount < params['min_amount'] or amount > params['max_amount']:
        return web.json_response({
            'success': False, 
            'message': f'Сумма должна быть от {params["min_amount"]} до {params["max_amount"]}₽'
        }, status=400)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        user_id = session[0]
        # Проверяем есть ли активные аренды ТОГО ЖЕ ТИПА
        cursor = await db.execute('SELECT id FROM rentals WHERE user_id = ? AND expiry > ? AND card_type = ?', 
                                (user_id, int(time.time()), card_type))
        active_rental = await cursor.fetchone()
        if active_rental:
            return web.json_response({
                'success': False, 
                'message': f'У вас уже есть активная данная видеокарта'
            }, status=400)

        cursor = await db.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        balance = (await cursor.fetchone())[0]
        if balance < amount:
            return web.json_response({'success': False, 'message': 'Недостаточно средств'}, status=400)

        await db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
        start_time = int(time.time())
        expiry = start_time + params['duration']
        created_at = int(time.time())
        unique_id = f'rental_{user_id}_{created_at}'
        await db.execute('INSERT INTO rentals (user_id, amount, start_time, expiry, created_at, card_type, profitability) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (user_id, amount, start_time, expiry, created_at, card_type, params['profitability']))
        await db.execute('INSERT INTO payments (user_id, unique_id, amount, status, type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, unique_id, -amount, 'completed', 'rental', created_at))
        await db.commit()

        asyncio.create_task(handle_rental_payout(user_id, amount, expiry, params['profitability']))
        return web.json_response({'success': True})

async def handle_rental_payout(user_id, amount, expiry, profitability):
    await asyncio.sleep(max(0, expiry - int(time.time())))
    async with aiosqlite.connect('users.db') as db:
        payout = amount * profitability
        await db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (payout, user_id))
        await db.execute('DELETE FROM rentals WHERE user_id = ? AND expiry = ?', (user_id, expiry))
        created_at = int(time.time())
        unique_id = f'rental_payout_{user_id}_{created_at}'
        await db.execute('INSERT INTO payments (user_id, unique_id, amount, status, type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, unique_id, payout, 'completed', 'rental', created_at))
        await db.commit()

async def get_rented_cards(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        user_id = session[0]
        cursor = await db.execute('SELECT amount, start_time, expiry, card_type, profitability FROM rentals WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        rentals = await cursor.fetchall()
        
        # Маппинг имен карт и длительностей
        card_names = {
            'gtx1060': 'GTX 1060',
            'rtx4090': 'RTX 4090',
            'rx580': 'RX 580'
        }
        card_durations = {
            'gtx1060': 24 * 3600,  # 24 часа
            'rtx4090': 72 * 3600,  # 72 часа
            'rx580': 48 * 3600     # 48 часов
        }
        
        return web.json_response({
            'success': True,
            'rentals': [{
                'amount': r[0], 
                'start_time': r[1], 
                'expiry': r[2],
                'card_name': card_names.get(r[3], 'Unknown Card'),
                'profitability': (r[4] * 100) if r[4] else 102,
                'duration': card_durations.get(r[3], 24 * 3600)
            } for r in rentals]
        })

async def create_withdrawal(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    data = await request.json()
    amount = data.get('amount')
    payeer_account = data.get('payeer_account')
    if not (10 <= amount <= 10000):
        return web.json_response({'success': False, 'message': 'Сумма должна быть от 10 до 10 000₽'}, status=400)
    if not payeer_account or not payeer_account.startswith('P'):
        return web.json_response({'success': False, 'message': 'Неверный PAYEER аккаунт'}, status=400)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        user_id = session[0]
        cursor = await db.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        balance = (await cursor.fetchone())[0]
        if balance < amount:
            return web.json_response({'success': False, 'message': 'Недостаточно средств'}, status=400)

        created_at = int(time.time())
        unique_id = f'payout_{user_id}_{created_at}'
        await db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
        await db.execute('INSERT INTO withdrawals (user_id, amount, payeer_account, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, amount, payeer_account, 'pending', created_at, created_at))
        await db.execute('INSERT INTO payments (user_id, unique_id, amount, status, type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, unique_id, -amount, 'pending', 'withdrawal', created_at))
        await db.commit()
        return web.json_response({'success': True})

async def get_withdrawal_requests(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        cursor = await db.execute('SELECT is_admin FROM users WHERE id = ?', (session[0],))
        is_admin = (await cursor.fetchone())[0]
        if not is_admin:
            return web.json_response({'success': False, 'message': 'Доступ запрещен'}, status=403)

        cursor = await db.execute('SELECT w.id, w.user_id, u.email, w.amount, w.payeer_account, w.status, w.created_at, w.updated_at FROM withdrawals w JOIN users u ON w.user_id = u.id WHERE w.status = ?', ('pending',))
        withdrawals = await cursor.fetchall()
        return web.json_response({
            'success': True,
            'withdrawals': [{'id': w[0], 'user_id': w[1], 'email': w[2], 'amount': w[3], 'payeer_account': w[4], 'status': w[5], 'created_at': w[6], 'updated_at': w[7]} for w in withdrawals]
        })

async def manage_withdrawal(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    data = await request.json()
    withdrawal_id = data.get('withdrawal_id')
    action = data.get('action')

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        cursor = await db.execute('SELECT is_admin FROM users WHERE id = ?', (session[0],))
        is_admin = (await cursor.fetchone())[0]
        if not is_admin:
            return web.json_response({'success': False, 'message': 'Доступ запрещен'}, status=403)

        cursor = await db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        withdrawal = await cursor.fetchone()
        if not withdrawal:
            return web.json_response({'success': False, 'message': 'Заявка не найдена'}, status=404)

        user_id, amount = withdrawal
        updated_at = int(time.time())
        if action == 'approve':
            await db.execute('UPDATE withdrawals SET status = ?, updated_at = ? WHERE id = ?', ('approved', updated_at, withdrawal_id))
            await db.execute('UPDATE payments SET status = ? WHERE user_id = ? AND amount = ? AND type = ?', ('completed', user_id, -amount, 'withdrawal'))
        elif action == 'reject':
            await db.execute('UPDATE withdrawals SET status = ?, updated_at = ? WHERE id = ?', ('rejected', updated_at, withdrawal_id))
            await db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
            await db.execute('UPDATE payments SET status = ? WHERE user_id = ? AND amount = ? AND type = ?', ('rejected', user_id, -amount, 'withdrawal'))
        else:
            return web.json_response({'success': False, 'message': 'Неверное действие'}, status=400)
        await db.commit()
        return web.json_response({'success': True})

async def add_money(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    data = await request.json()
    user_id = data.get('user_id')
    amount = data.get('amount')
    if not user_id or not amount or amount <= 0:
        return web.json_response({'success': False, 'message': 'Неверные параметры'}, status=400)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        cursor = await db.execute('SELECT is_admin FROM users WHERE id = ?', (session[0],))
        is_admin = (await cursor.fetchone())[0]
        if not is_admin:
            return web.json_response({'success': False, 'message': 'Доступ запрещен'}, status=403)

        cursor = await db.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            return web.json_response({'success': False, 'message': 'Пользователь не найден'}, status=404)

        created_at = int(time.time())
        unique_id = f'admin_add_{user_id}_{created_at}'
        await db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
        await db.execute('INSERT INTO payments (user_id, unique_id, amount, status, type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, unique_id, amount, 'completed', 'admin_add', created_at))
        await db.commit()
        return web.json_response({'success': True})

async def deduct_money(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    data = await request.json()
    user_id = data.get('user_id')
    amount = data.get('amount')
    if not user_id or not amount or amount <= 0:
        return web.json_response({'success': False, 'message': 'Неверные параметры'}, status=400)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        cursor = await db.execute('SELECT is_admin FROM users WHERE id = ?', (session[0],))
        is_admin = (await cursor.fetchone())[0]
        if not is_admin:
            return web.json_response({'success': False, 'message': 'Доступ запрещен'}, status=403)

        cursor = await db.execute('SELECT id, balance FROM users WHERE id = ?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            return web.json_response({'success': False, 'message': 'Пользователь не найден'}, status=404)

        if user[1] < amount:
            return web.json_response({'success': False, 'message': 'Недостаточно средств'}, status=400)

        created_at = int(time.time())
        unique_id = f'admin_deduct_{user_id}_{created_at}'
        await db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
        await db.execute('INSERT INTO payments (user_id, unique_id, amount, status, type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, unique_id, -amount, 'completed', 'admin_deduct', created_at))
        await db.commit()
        return web.json_response({'success': True})

async def get_user_info(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    data = await request.json()
    user_id = data.get('user_id')
    email = data.get('email')
    if not user_id and not email:
        return web.json_response({'success': False, 'message': 'Укажите ID или email пользователя'}, status=400)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        cursor = await db.execute('SELECT is_admin FROM users WHERE id = ?', (session[0],))
        is_admin = (await cursor.fetchone())[0]
        if not is_admin:
            return web.json_response({'success': False, 'message': 'Доступ запрещен'}, status=403)

        if user_id:
            cursor = await db.execute('SELECT id, email, balance, is_admin FROM users WHERE id = ?', (user_id,))
        else:
            cursor = await db.execute('SELECT id, email, balance, is_admin FROM users WHERE email = ?', (email,))

        user = await cursor.fetchone()
        if not user:
            return web.json_response({'success': False, 'message': 'Пользователь не найден'}, status=404)

        cursor = await db.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user[0],))
        referral_count = (await cursor.fetchone())[0]

        return web.json_response({
            'success': True,
            'user': {
                'id': user[0],
                'email': user[1],
                'balance': user[2],
                'is_admin': user[3],
                'referral_count': referral_count
            }
        })

async def get_top_stats(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        cursor = await db.execute('SELECT is_admin FROM users WHERE id = ?', (session[0],))
        is_admin = (await cursor.fetchone())[0]
        if not is_admin:
            return web.json_response({'success': False, 'message': 'Доступ запрещен'}, status=403)

        # Top 5 richest users
        cursor = await db.execute('SELECT id, email, balance FROM users ORDER BY balance DESC LIMIT 5')
        top_rich = await cursor.fetchall()
        
        # Top 5 users by referrals
        cursor = await db.execute('''
            SELECT u.id, u.email, COUNT(r.referred_id) as referral_count
            FROM users u
            LEFT JOIN referrals r ON u.id = r.referrer_id
            GROUP BY u.id, u.email
            ORDER BY referral_count DESC, u.id
            LIMIT 5
        ''')
        top_referrers = await cursor.fetchall()

        return web.json_response({
            'success': True,
            'top_rich': [{'id': r[0], 'email': r[1], 'balance': r[2]} for r in top_rich],
            'top_referrers': [{'id': r[0], 'email': r[1], 'referral_count': r[2]} for r in top_referrers]
        })

async def get_history(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        user_id = session[0]
        page = int(request.query.get('page', 1))
        per_page = int(request.query.get('per_page', 10))
        offset = (page - 1) * per_page

        cursor = await db.execute('SELECT amount, status, created_at, unique_id, type FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
                                (user_id, per_page, offset))
        payments = await cursor.fetchall()
        cursor = await db.execute('SELECT COUNT(*) FROM payments WHERE user_id = ?', (user_id,))
        total = (await cursor.fetchone())[0]

        history = []
        for payment in payments:
            amount, status, created_at, unique_id, payment_type = payment
            history.append({
                'type': payment_type,
                'amount': amount,
                'status': status,
                'created_at': created_at,
                'url': f'https://t.me/XPayBot?startapp={unique_id}' if unique_id and payment_type == 'deposit' else ''
            })

        history.sort(key=lambda x: x['created_at'], reverse=True)
        history = history[:per_page]

        return web.json_response({
            'success': True,
            'history': history,
            'total': total,
            'page': page,
            'per_page': per_page
        })

async def create_payment(request):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return web.json_response({'success': False, 'message': 'Не авторизован'}, status=401)

    data = await request.json()
    amount = data.get('amount')
    if not (10 <= amount <= 10000):
        return web.json_response({'success': False, 'message': 'Сумма должна быть от 10 до 10 000₽'}, status=400)

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM sessions WHERE session_token = ? AND expiry > ?',
                                (session_token, int(time.time())))
        session = await cursor.fetchone()
        if not session:
            return web.json_response({'success': False, 'message': 'Сессия истекла'}, status=401)

        user_id = session[0]
        async with aiohttp.ClientSession() as http_session:
            try:
                async with http_session.post(
                    f'https://xpay.bot-wizard.org:5000/shop{SHOP_ID}/{SHOP_TOKEN}/createInvoice',
                    json={
                        'amount': amount,
                        'description': 'Пополнение баланса',
                        'payload': f'user_{user_id}'
                    },
                    ssl=False
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        created_at = int(time.time())
                        unique_id = data.get('unique_id') or data['url'].split('startapp=')[1]
                        await db.execute('INSERT INTO payments (user_id, unique_id, amount, status, type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                                    (user_id, unique_id, amount, 'pending', 'deposit', created_at))
                        await db.commit()
                        print(f"Created payment with unique_id: *")
                        return web.json_response({'success': True, 'url': data['url']})
                    elif response.status == 429:
                        print("Rate limit reached for createInvoice")
                        return web.json_response({'success': False, 'message': 'Слишком много запросов, попробуйте позже'}, status=429)
                    else:
                        print(f"Failed to create payment, status: {response.status}")
                        return web.json_response({'success': False, 'message': 'Ошибка создания платежа'}, status=response.status)
            except aiohttp.ClientError as e:
                print(f"ClientError in create_payment: {str(e)}")
                return web.json_response({'success': False, 'message': 'Ошибка сервера XPay'}, status=500)

async def get_stats(request):
    async with aiosqlite.connect('users.db') as db:
        # Количество пользователей
        cursor = await db.execute('SELECT COUNT(*) FROM users')
        total_users = (await cursor.fetchone())[0]
        
        # Сумма всех пополнений
        cursor = await db.execute('SELECT SUM(amount) FROM payments WHERE type = "deposit" AND status = "completed"')
        total_deposits = (await cursor.fetchone())[0] or 0
        
        # Сумма всех выплат
        cursor = await db.execute('SELECT SUM(amount) FROM payments WHERE type = "withdrawal" AND status = "completed"')
        total_withdrawn = abs((await cursor.fetchone())[0] or 0)
        
        # Дней работы (с момента первого платежа)
        cursor = await db.execute('SELECT MIN(created_at) FROM payments')
        first_payment_time = (await cursor.fetchone())[0]
        if first_payment_time:
            days_running = (int(time.time()) - first_payment_time) // 86400
        else:
            days_running = 0
        
        return web.json_response({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_deposits': total_deposits,
                'total_withdrawn': total_withdrawn,
                'days_running': days_running
            }
        })

async def check_payments():
    while True:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute('SELECT user_id, unique_id, amount FROM payments WHERE status = ?', ('pending',))
            pending_payments = await cursor.fetchall()
            print(f"Found {len(pending_payments)} pending payments")

            async with aiohttp.ClientSession() as http_session:
                try:
                    async with http_session.get(
                        f'https://xpay.bot-wizard.org:5000/shop{SHOP_ID}/{SHOP_TOKEN}/getUpdates',
                        ssl=False
                    ) as response:
                        if response.status == 201:
                            updates = await response.json()
                            for update in updates:
                                if update.get('endDate'):
                                    unique_id = update.get('unique_id')
                                    if not unique_id:
                                        continue
                                    
                                    cursor = await db.execute(
                                        '''SELECT user_id, amount FROM payments 
                                        WHERE (unique_id = ? OR unique_id = ? OR unique_id = ?) 
                                        AND status = "pending"''',
                                        (unique_id, 
                                         f"inv-{unique_id}",
                                         unique_id.replace("inv-", ""))
                                    )
                                    payment = await cursor.fetchone()
                                    
                                    if payment:
                                        user_id, amount = payment
                                        try:
                                            await db.execute('BEGIN TRANSACTION')
                                            await db.execute(
                                                'UPDATE users SET balance = balance + ? WHERE id = ?',
                                                (amount, user_id)
                                            )
                                            await db.execute(
                                                'UPDATE payments SET status = ? WHERE (unique_id = ? OR unique_id = ? OR unique_id = ?)',
                                                ('completed', 
                                                 unique_id,
                                                 f"inv-{unique_id}",
                                                 unique_id.replace("inv-", ""))
                                            )
                                            cursor = await db.execute(
                                                'SELECT referrer_id FROM users WHERE id = ?',
                                                (user_id,)
                                            )
                                            referrer = await cursor.fetchone()
                                            if referrer and referrer[0]:
                                                referral_bonus = amount * 0.02
                                                await db.execute(
                                                    'UPDATE users SET balance = balance + ? WHERE id = ?',
                                                    (referral_bonus, referrer[0])
                                                )
                                            await db.commit()
                                            print(f"Successfully processed payment *")
                                        except Exception as e:
                                            await db.rollback()
                                            print(f"Error processing payment *")
                                    else:
                                        print(f"Payment * not found in database or already processed")
                        elif response.status == 429:
                            print('Rate limit reached for getUpdates, retrying later')
                        else:
                            print(f"Unexpected response status: *")
                except aiohttp.ClientError as e:
                    print(f"ClientError in check_payments: *")
        
        await asyncio.sleep(60)

app = web.Application()
app.router.add_post('/register', register)
app.router.add_post('/login', login)
app.router.add_post('/check_session', check_session)
app.router.add_post('/logout', logout)
app.router.add_post('/rent', rent_card)
app.router.add_get('/rented_cards', get_rented_cards)
app.router.add_get('/history', get_history)
app.router.add_post('/create_payment', create_payment)
app.router.add_post('/create_withdrawal', create_withdrawal)
app.router.add_get('/withdrawal_requests', get_withdrawal_requests)
app.router.add_post('/manage_withdrawal', manage_withdrawal)
app.router.add_post('/add_money', add_money)
app.router.add_post('/deduct_money', deduct_money)
app.router.add_post('/get_user_info', get_user_info)
app.router.add_get('/get_stats', get_stats)
app.router.add_get('/get_top_stats', get_top_stats)
app.router.add_static('/', './')

async def main():
    await init_db()
    asyncio.create_task(check_payments())
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Server started at http://0.0.0.0:8080")
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())