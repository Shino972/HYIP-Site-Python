document.addEventListener('DOMContentLoaded', () => {
    const pagesWithNav = ['dashboard.html', 'history.html', 'payment.html', 'withdraw.html', 'admin.html'];

    if (pagesWithNav.some(page => window.location.pathname.includes(page))) {
        checkSession();
    }

    if (window.location.pathname.includes('dashboard.html')) {
        loadRentedCards();
        setInterval(loadRentedCards, 30000);
    } else if (window.location.pathname.includes('payment.html')) {
        setupPaymentForm();
    } else if (window.location.pathname.includes('index.html')) {
        setupReferral();
        loadStats();
    } else if (window.location.pathname.includes('history.html')) {
        loadHistory(1);
    } else if (window.location.pathname.includes('withdraw.html')) {
        setupWithdrawForm();
    } else if (window.location.pathname.includes('admin.html')) {
        loadWithdrawalRequests();
        setupAdminForms();
        loadTopStats();
    }

    // Mobile menu toggle
    const mobileMenuButton = document.querySelector('.nav-mobile-menu');
    const mobileMenu = document.querySelector('.nav-links-mobile');
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('active');
        });
    }
});

async function checkSession() {
    try {
        const response = await fetch('/check_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            if (window.location.pathname.includes('dashboard.html')) {
                document.getElementById('userId').textContent = data.user_id;
                document.getElementById('userBalance').textContent = parseFloat(data.balance).toFixed(2);
                const referralLink = `https://gpumining.fun/?ref=${data.user_id}`;
                document.getElementById('referralLink').textContent = referralLink;
                document.getElementById('referralLink').href = referralLink;
                document.getElementById('referralCount').textContent = data.referral_count || 0;
            }

            if (data.is_admin) {
                // Десктопное меню
                const desktopMenu = document.querySelector('.hidden.md\\:flex.items-center.space-x-1');
                if (desktopMenu && !desktopMenu.querySelector('a[href="admin.html"]')) {
                    const adminLink = document.createElement('a');
                    adminLink.href = 'admin.html';
                    adminLink.className = 'px-4 py-2 rounded-lg hover:bg-white/10 transition-all flex items-center';
                    adminLink.innerHTML = '<i class="fas fa-user-shield mr-2"></i> Админ-панель';
                    
                    const logoutLink = desktopMenu.querySelector('a[onclick="logout()"]');
                    if (logoutLink) {
                        desktopMenu.insertBefore(adminLink, logoutLink);
                    } else {
                        desktopMenu.appendChild(adminLink);
                    }
                }

                const mobileMenu = document.getElementById('mobileMenu');
                if (mobileMenu && !mobileMenu.querySelector('a[href="admin.html"]')) {
                    const adminMobileLink = document.createElement('a');
                    adminMobileLink.href = 'admin.html';
                    adminMobileLink.className = 'block px-4 py-3 hover:bg-white/10 rounded-lg transition-all';
                    adminMobileLink.innerHTML = '<i class="fas fa-user-shield mr-3"></i> Админ-панель';
                    
                    const logoutMobileLink = mobileMenu.querySelector('a[onclick="logout()"]');
                    if (logoutMobileLink) {
                        mobileMenu.insertBefore(adminMobileLink, logoutMobileLink);
                    } else {
                        mobileMenu.appendChild(adminMobileLink);
                    }
                }
            }
        } else {
            window.location.href = 'index.html';
        }
    } catch (error) {
        window.location.href = 'index.html';
    }
}

function showTab(tabName) {
    document.querySelectorAll('.form').forEach(form => {
        form.classList.remove('active');
    });
    
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    document.getElementById(tabName + 'Form').classList.add('active');
    
    document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
}

function setupReferral() {
    const urlParams = new URLSearchParams(window.location.search);
    const refId = urlParams.get('ref');
    if (refId) {
        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.dataset.refId = refId;
        }
    }
}

document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errorP = document.getElementById('loginError');

    errorP.textContent = '';
    errorP.className = 'text-red-500 text-sm mt-2 hidden';

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        if (data.success) {
            window.location.href = data.is_admin ? 'admin.html' : 'dashboard.html';
        } else {
            errorP.textContent = data.message || 'Ошибка авторизации: проверьте email или пароль';
            errorP.classList.remove('hidden');
            setTimeout(() => {
                errorP.classList.add('hidden');
                errorP.textContent = '';
            }, 5000);
        }
    } catch (error) {
        errorP.textContent = 'Ошибка сервера: попробуйте позже';
        errorP.classList.remove('hidden');
        setTimeout(() => {
            errorP.classList.add('hidden');
            errorP.textContent = '';
        }, 5000);
    }
});

document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const refId = e.target.dataset.refId || null;
    const errorP = document.getElementById('registerError');

    errorP.textContent = '';
    errorP.className = 'text-red-500 text-sm mt-2 hidden';

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, ref_id: refId })
        });
        const data = await response.json();
        if (data.success) {
            window.location.href = 'dashboard.html';
        } else {
            errorP.textContent = data.message || 'Ошибка регистрации: проверьте введенные данные';
            errorP.classList.remove('hidden');
            setTimeout(() => {
                errorP.classList.add('hidden');
                errorP.textContent = '';
            }, 5000);
        }
    } catch (error) {
        errorP.textContent = 'Ошибка сервера: попробуйте позже';
        errorP.classList.remove('hidden');
        setTimeout(() => {
            errorP.classList.add('hidden');
            errorP.textContent = '';
        }, 5000);
    }
});

async function logout() {
    try {
        await fetch('/logout', { 
            method: 'POST',
            credentials: 'include'
        });
        window.location.href = 'index.html';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = 'index.html';
    }
}

// Обработка всех форм аренды
document.querySelectorAll('.rent-form').forEach(form => {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const cardType = e.target.dataset.card;
        const amountInput = e.target.querySelector('input[type="number"]');
        const errorP = e.target.querySelector('.rent-error');
        const amount = parseFloat(amountInput.value);

        // Проверки для разных карт
        let minAmount, maxAmount, errorMessage;
        switch(cardType) {
            case 'gtx1060':
                minAmount = 100;
                maxAmount = 150;
                errorMessage = 'Сумма аренды должна быть от 100 до 150₽';
                break;
            case 'rtx4090':
                minAmount = 1000;
                maxAmount = 5000;
                errorMessage = 'Сумма аренды должна быть от 1000 до 5000₽';
                break;
            case 'rx580':
                minAmount = 500;
                maxAmount = 1000;
                errorMessage = 'Сумма аренды должна быть от 500 до 1000₽';
                break;
            default:
                minAmount = 100;
                maxAmount = 150;
                errorMessage = 'Неверный тип карты';
        }

        if (amount < minAmount || amount > maxAmount) {
            errorP.textContent = errorMessage;
            return;
        }

        try {
            const response = await fetch('/rent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    amount,
                    card_type: cardType 
                })
            });
            const data = await response.json();
            if (data.success) {
                errorP.textContent = '';
                alert('Видеокарта арендована успешно!');
                await checkSession();
                await loadRentedCards();
            } else {
                errorP.textContent = data.message || 'Ошибка аренды';
            }
        } catch (error) {
            errorP.textContent = 'Ошибка сервера';
        }
    });
});

async function loadRentedCards() {
    try {
        const response = await fetch('/rented_cards', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        const rentedContainer = document.getElementById('rentedList');
        const cardsList = rentedContainer.querySelector('.space-y-4');
        const emptyState = rentedContainer.querySelector('#noRentedItems');

        cardsList.innerHTML = '';
        
        if (data.rentals && data.rentals.length > 0) {
            emptyState.classList.add('hidden');
            
            data.rentals.forEach(rental => {
                const timeLeft = Math.max(0, rental.expiry - Math.floor(Date.now() / 1000));
                const hours = Math.floor(timeLeft / 3600);
                const minutes = Math.floor((timeLeft % 3600) / 60);
                const progress = Math.min(100, Math.max(0, Math.floor((1 - timeLeft / (rental.duration || 24 * 3600)) * 100)));
                const endDate = new Date(rental.expiry * 1000);
                
                const endDateFormatted = endDate.toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                const isActive = timeLeft > 0;
                const statusText = isActive ? 'Активна' : 'Завершена';
                const statusClass = isActive ? 'bg-blue-600 text-white' : 'bg-green-600 text-white';
                
                const card = document.createElement('div');
                card.className = `border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-300 ${isActive ? '' : 'opacity-80'}`;
                card.innerHTML = `
                    <div class="flex flex-col md:flex-row md:items-center md:justify-between">
                        <!-- Левая часть - информация о карте -->
                        <div class="flex items-start space-x-4 mb-3 md:mb-0">
                            <div class="${isActive ? 'bg-blue-600' : 'bg-gray-600'} p-3 rounded-lg">
                                <i class="fas fa-microchip ${isActive ? 'text-blue' : 'text-blue'} text-xl"></i>
                            </div>
                            
                            <div>
                                <h4 class="font-semibold text-lg flex items-center text-white px-2 py-1 rounded">
                                    ${rental.card_name || 'GTX 1060'}
                                    <span class="ml-2 ${statusClass} px-2 py-0.5 rounded-full text-xs font-medium text-white">
                                        ${statusText}
                                    </span>
                                </h4>
                                
                                <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-gray-300 mt-1">
                                    <div class="flex items-center">
                                        <i class="fas fa-coins mr-2 text-yellow-500"></i>
                                        <span>Инвестировано: <span class="font-medium">${rental.amount.toFixed(2)}₽</span></span>
                                    </div>
                                    <div class="flex items-center">
                                        <i class="fas fa-chart-line mr-2 text-green-500"></i>
                                        <span>Доходность: <span class="font-medium">${rental.profitability || 102}%</span></span>
                                    </div>
                                    <div class="flex items-center">
                                        <i class="far ${isActive ? 'fa-clock' : 'fa-check-circle'} mr-2 ${isActive ? 'text-purple-500' : 'text-green-500'}"></i>
                                        <span>${isActive ? 'Осталось' : 'Статус'}: <span class="font-medium">${isActive ? `${hours}ч ${minutes}м` : 'Выплачено ' + (rental.amount * ((rental.profitability || 102) / 100)).toFixed(2) + '₽'}</span></span>
                                    </div>
                                    <div class="flex items-center">
                                        <i class="fas ${isActive ? 'fa-calendar-check' : 'fa-calendar-times'} mr-2 ${isActive ? 'text-blue-500' : 'text-red-500'}"></i>
                                        <span>${isActive ? 'Завершится' : 'Завершена'}: <span class="font-medium">${endDateFormatted}</span></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Правая часть - прогресс бар и доход -->
                        <div class="flex flex-col items-end">
                            <div class="w-full md:w-48 mb-2">
                                <div class="flex justify-between text-xs text-white mb-1">
                                    <span>Прогресс</span>
                                    <span>${isActive ? progress : 100}%</span>
                                </div>
                                <div class="w-full bg-gray-700 rounded-full h-2">
                                    <div class="${isActive ? 'bg-blue-600' : 'bg-green-500'} h-2 rounded-full" style="width: ${isActive ? progress : 100}%"></div>
                                </div>
                            </div>
                            
                            <div class="${isActive ? 'bg-blue-600' : 'bg-green-600'} px-3 py-1 rounded-lg text-center">
                                <p class="text-xs text-white">${isActive ? 'Ожидаемый доход' : 'Полученный доход'}</p>
                                <p class="font-semibold text-white">
                                    +${(rental.amount * ((rental.profitability || 102) / 100 - 1)).toFixed(2)}₽ 
                                    ${isActive ? `(${(rental.amount * (rental.profitability || 102) / 100).toFixed(2)}₽ всего)` : ''}
                                </p>
                            </div>
                        </div>
                    </div>
                `;
                
                cardsList.appendChild(card);
            });
        } else {
            cardsList.innerHTML = '';
            emptyState.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error loading rented cards:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-50 border-l-4 border-red-500 p-4 mb-4';
        errorDiv.innerHTML = `
            <div class="flex">
                <div class="flex-shrink-0">
                    <i class="fas fa-exclamation-circle text-red-500"></i>
                </div>
                <div class="ml-3">
                    <p class="text-sm text-red-700">Произошла ошибка при загрузке арендованных видеокарт. Пожалуйста, попробуйте позже.</p>
                </div>
            </div>
        `;
        rentedContainer.insertBefore(errorDiv, rentedContainer.firstChild);
    }
}

async function loadHistory(page = 1, perPage = 10) {
    try {
        const response = await fetch(`/history?page=${page}&per_page=${perPage}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = '';
        if (data.history && data.history.length > 0) {
            const table = document.createElement('table');
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';
            table.innerHTML = `
                <tr>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Тип</th>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Сумма</th>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Статус</th>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Дата</th>
                </tr>
            `;
            data.history.forEach(transaction => {
                const tr = document.createElement('tr');
                tr.className = 'history-item';
                const date = new Date(transaction.created_at * 1000).toLocaleString('ru-RU');
                let typeText = transaction.type === 'deposit' ? 'Пополнение' :
                              transaction.type === 'withdrawal' ? 'Вывод' :
                              transaction.type === 'rental' ? 'Аренда' :
                              transaction.type === 'admin_add' ? 'Админ: Пополнение' :
                              transaction.type === 'admin_deduct' ? 'Админ: Снятие' : transaction.type;
                let statusText = transaction.status === 'pending' ? 'Ожидает' :
                                transaction.status === 'completed' ? 'Завершено' : 'Отклонено';
                tr.innerHTML = `
                    <td style="padding: 10px; color: aqua;">${typeText}</td>
                    <td style="padding: 10px; color: aqua;">${transaction.amount.toFixed(2)}₽</td>
                    <td style="padding: 10px; color: aqua;">${statusText}</td>
                    <td style="padding: 10px; color: aqua;">${date}</td>
                `;
                if (transaction.type === 'deposit' && transaction.url) {
                    tr.style.cursor = 'pointer';
                    tr.addEventListener('click', () => window.location.href = transaction.url);
                }
                table.appendChild(tr);
            });
            historyList.appendChild(table);

            // Update pagination
            const totalPages = Math.ceil(data.total / data.per_page);
            const pageInfo = document.getElementById('pageInfo');
            const prevPage = document.getElementById('prevPage');
            const nextPage = document.getElementById('nextPage');
            pageInfo.textContent = `Страница ${data.page} из ${totalPages}`;
            pageInfo.style.color = 'white';
            prevPage.disabled = data.page <= 1;
            nextPage.disabled = data.page >= totalPages;
            prevPage.onclick = () => loadHistory(data.page - 1, perPage);
            nextPage.onclick = () => loadHistory(data.page + 1, perPage);
        } else {
            historyList.innerHTML = '<p>Нет операций</p>';
        }
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('historyList').innerHTML = '<p>Ошибка загрузки истории</p>';
    }
}

function setupPaymentForm() {
    const paymentInput = document.getElementById('paymentAmount');
    const payButton = document.getElementById('payButton');
    const errorP = document.getElementById('paymentError');

    paymentInput.addEventListener('input', () => {
        const amount = parseFloat(paymentInput.value);
        payButton.disabled = isNaN(amount) || amount < 10 || amount > 10000;
    });

    document.getElementById('paymentForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const amount = parseFloat(paymentInput.value);
        errorP.textContent = '';

        if (amount < 10 || amount > 10000) {
            errorP.textContent = 'Сумма должна быть от 10 до 10 000₽';
            return;
        }

        try {
            const response = await fetch('/create_payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount })
            });
            const data = await response.json();
            if (data.success) {
                window.location.href = data.url;
            } else {
                errorP.textContent = data.message || 'Ошибка создания платежа';
            }
        } catch (error) {
            errorP.textContent = 'Ошибка сервера';
        }
    });
}

function setupWithdrawForm() {
    const withdrawInput = document.getElementById('withdrawAmount');
    const payeerInput = document.getElementById('payeerAccount');
    const withdrawButton = document.getElementById('withdrawButton');
    const errorP = document.getElementById('withdrawError');

    function validateForm() {
        const amount = parseFloat(withdrawInput.value);
        const payeer = payeerInput.value;
        withdrawButton.disabled = !amount || amount < 10 || amount > 10000 || !payeer || !/^P\d+$/.test(payeer);
    }

    withdrawInput.addEventListener('input', validateForm);
    payeerInput.addEventListener('input', validateForm);

    document.getElementById('withdrawForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const amount = parseFloat(withdrawInput.value);
        const payeer_account = payeerInput.value;
        errorP.textContent = '';

        try {
            const response = await fetch('/create_withdrawal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount, payeer_account })
            });
            const data = await response.json();
            if (data.success) {
                window.location.href = 'dashboard.html';
            } else {
                errorP.textContent = data.message || 'Ошибка создания заявки на вывод';
            }
        } catch (error) {
            errorP.textContent = 'Ошибка сервера';
        }
    });
}

function setupAdminForms() {
    document.getElementById('addMoneyForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userId = document.getElementById('addUserId').value;
        const amount = parseFloat(document.getElementById('addAmount').value);
        const errorP = document.getElementById('addMoneyError');

        if (amount <= 0) {
            errorP.textContent = 'Сумма должна быть больше 0';
            return;
        }

        try {
            const response = await fetch('/add_money', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, amount })
            });
            const data = await response.json();
            if (data.success) {
                errorP.textContent = '';
                alert('Деньги успешно добавлены!');
                window.location.reload();
            } else {
                errorP.textContent = data.message || 'Ошибка добавления денег';
            }
        } catch (error) {
            errorP.textContent = 'Ошибка сервера';
        }
    });

    document.getElementById('deductMoneyForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userId = document.getElementById('deductUserId').value;
        const amount = parseFloat(document.getElementById('deductAmount').value);
        const errorP = document.getElementById('deductMoneyError');

        if (amount <= 0) {
            errorP.textContent = 'Сумма должна быть больше 0';
            return;
        }

        try {
            const response = await fetch('/deduct_money', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, amount })
            });
            const data = await response.json();
            if (data.success) {
                errorP.textContent = '';
                alert('Деньги успешно сняты!');
                window.location.reload();
            } else {
                errorP.textContent = data.message || 'Ошибка снятия денег';
            }
        } catch (error) {
            errorP.textContent = 'Ошибка сервера';
        }
    });
    document.getElementById('userInfoForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userIdOrEmail = document.getElementById('userIdOrEmail').value;
        const resultDiv = document.getElementById('userInfoResult');

        try {
            const response = await fetch('/get_user_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(
                    isNaN(userIdOrEmail) ? { email: userIdOrEmail } : { user_id: parseInt(userIdOrEmail) }
                )
            });
            const data = await response.json();
            if (data.success) {
                const user = data.user;
                resultDiv.innerHTML = `
                    <div class="bg-green-200 border-l-4 border-green-700 p-4 text-green-900">
                        <p><strong>ID:</strong> ${user.id}</p>
                        <p><strong>Email:</strong> ${user.email}</p>
                        <p><strong>Баланс:</strong> ${user.balance.toFixed(2)}₽</p>
                        <p><strong>Админ:</strong> ${user.is_admin ? 'Да' : 'Нет'}</p>
                        <p><strong>Количество рефералов:</strong> ${user.referral_count}</p>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `
                    <div class="bg-red-200 border-l-4 border-red-700 p-4">
                        <p class="text-red-900">${data.message || 'Ошибка получения информации'}</p>
                    </div>
                `;
            }
        } catch (error) {
            resultDiv.innerHTML = `
                <div class="bg-red-200 border-l-4 border-red-700 p-4">
                    <p class="text-red-900">Ошибка сервера</p>
                </div>
                `;
        }
    });
}

async function loadTopStats() {
    try {
        const response = await fetch('/get_top_stats', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        const topRichList = document.getElementById('topRichList');
        const topReferrersList = document.getElementById('topReferrersList');

        if (data.success) {
            // Top Rich
            if (data.top_rich && data.top_rich.length > 0) {
                topRichList.innerHTML = data.top_rich.map((user, index) => `
                    <div class="flex items-center justify-between p-2 border-b border-gray-200">
                        <span class="flex items-center">
                            <span class="mr-2 text-yellow-500">${index + 1}.</span>
                            <span>${user.email} (ID: ${user.id})</span>
                        </span>
                        <span class="font-semibold text-green-600">${user.balance.toFixed(2)}₽</span>
                    </div>
                `).join('');
            } else {
                topRichList.innerHTML = '<p>Нет данных</p>';
            }

            // Top Referrers
            if (data.top_referrers && data.top_referrers.length > 0) {
                topReferrersList.innerHTML = data.top_referrers.map((user, index) => `
                    <div class="flex items-center justify-between p-2 border-b border-gray-200">
                        <span class="flex items-center">
                            <span class="mr-2 text-yellow-500">${index + 1}.</span>
                            <span>${user.email} (ID: ${user.id})</span>
                        </span>
                        <span class="font-semibold text-blue-600">${user.referral_count} рефералов</span>
                    </div>
                `).join('');
            } else {
                topReferrersList.innerHTML = '<p>Нет данных</p>';
            }
        } else {
            topRichList.innerHTML = '<p>Ошибка загрузки данных</p>';
            topReferrersList.innerHTML = '<p>Ошибка загрузки данных</p>';
        }
    } catch (error) {
        console.error('Error loading top stats:', error);
        document.getElementById('topRichList').innerHTML = '<p>Ошибка загрузки данных</p>';
        document.getElementById('topReferrersList').innerHTML = '<p>Ошибка загрузки данных</p>';
    }
}

async function loadWithdrawalRequests() {
    try {
        const response = await fetch('/withdrawal_requests', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        const withdrawalList = document.getElementById('withdrawalList');
        withdrawalList.innerHTML = '';
        if (data.success && data.withdrawals && data.withdrawals.length > 0) {
            const table = document.createElement('table');
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';
            table.innerHTML = `
                <tr>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Пользователь</th>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Сумма</th>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white; ">PAYEER</th>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Дата</th>
                    <th style="border-bottom: 1px solid #eee; padding: 10px; color: white;">Действия</th>
                </tr>
            `;
            data.withdrawals.forEach(withdrawal => {
                const tr = document.createElement('tr');
                const date = new Date(withdrawal.created_at * 1000).toLocaleString('ru-RU');
                tr.innerHTML = `
                    <td style="padding: 10px; color: white;">${withdrawal.email}</td>
                    <td style="padding: 10px; color: white;">${withdrawal.amount.toFixed(2)}₽</td>
                    <td style="padding: 10px; color: white;">${withdrawal.payeer_account}</td>
                    <td style="padding: 10px; color: white;">${date}</td>
                    <td style="padding: 10px;">
                        <button onclick="manageWithdrawal(${withdrawal.id}, 'approve')" class="px-3 py-1 bg-blue-600 text-white rounded-md font-semibold hover:bg-indigo-700 transition-all mr-2">Одобрить</button>
                        <button onclick="manageWithdrawal(${withdrawal.id}, 'reject')" class="px-3 py-1 bg-red-600 text-white rounded-md font-semibold hover:bg-red-700 transition-all">Отклонить</button>
                    </td>
                `;
                table.appendChild(tr);
            });
            withdrawalList.appendChild(table);
        } else {
            withdrawalList.innerHTML = '<p>Нет заявок на вывод</p>';
        }
    } catch (error) {
        console.error('Error loading withdrawal requests:', error);
        document.getElementById('withdrawalList').innerHTML = '<p>Ошибка загрузки заявок</p>';
    }
}

async function manageWithdrawal(withdrawalId, action) {
    try {
        const response = await fetch('/manage_withdrawal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ withdrawal_id: withdrawalId, action })
        });
        const data = await response.json();
        if (data.success) {
            loadWithdrawalRequests();
        } else {
            alert(data.message || 'Ошибка управления заявкой');
        }
    } catch (error) {
        alert('Ошибка сервера');
    }
}

async function loadStats() {
    try {
        const response = await fetch('/get_stats');
        const data = await response.json();
        if (data.success) {
            // Форматируем числа с разделителями тысяч
            const formatNumber = (num) => {
                return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
            };

            document.getElementById('totalUsers').textContent = formatNumber(data.stats.total_users);
            document.getElementById('totalDeposits').textContent = formatNumber(data.stats.total_deposits.toFixed(2)) + '₽';
            document.getElementById('totalWithdrawn').textContent = formatNumber(data.stats.total_withdrawn.toFixed(2)) + '₽';
            document.getElementById('daysRunning').textContent = formatNumber(data.stats.days_running);
            
            // Анимация счетчиков
            animateValue('totalUsers', 0, data.stats.total_users, 2000);
            animateValue('totalDeposits', 0, data.stats.total_deposits, 2000);
            animateValue('totalWithdrawn', 0, data.stats.total_withdrawn, 2000);
            animateValue('daysRunning', 0, data.stats.days_running, 2000);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        let value;
        if (id === 'totalDeposits' || id === 'totalWithdrawn') {
            value = (progress * (end - start) + start).toFixed(2);
            if (progress === 1) value = end.toFixed(2);
            obj.textContent = value + '₽';
        } else {
            value = Math.floor(progress * (end - start) + start);
            obj.textContent = value;
        }
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}