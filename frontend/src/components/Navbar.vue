<template>
    <nav class="navbar">
        <div class="tab-bar-screen_tab_bar__3OvHk">
            <div class="tab-bar-screen_tab_bar_container__FZos1">
                <router-link to="/"
                             class="tab-bar-screen_tab_bar_item__fPG6j "
                             :class="{ 'tab-bar-screen_active__pBXjN': $route.path === '/' }"
                >
                    <div class="tab-bar-screen_icon__xrTCK">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
                             viewBox="0 0 24 24"
                             fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                             stroke-linejoin="round" class="tabler-icon tabler-icon-home ">
                            <path d="M5 12l-2 0l9 -9l9 9l-2 0"></path>
                            <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7"></path>
                            <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6"></path>
                        </svg>
                    </div>
                    <div class="nav-link">Главная</div>
                </router-link>
                <router-link to="/catalog"
                             class="tab-bar-screen_tab_bar_item__fPG6j"
                             :class="{ 'tab-bar-screen_active__pBXjN': ['/catalog', '/products'].some(path => $route.path.startsWith(path)) }"
                >
                    <div class="tab-bar-screen_icon__xrTCK">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
                             viewBox="0 0 24 24"
                             fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                             stroke-linejoin="round" class="tabler-icon tabler-icon-category-2 ">
                            <path d="M14 4h6v6h-6z"></path>
                            <path d="M4 14h6v6h-6z"></path>
                            <path d="M17 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"></path>
                            <path d="M7 7m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"></path>
                        </svg>
                    </div>
                    <div class="nav-link">Каталог</div>
                </router-link>
                <router-link to="/favorite"
                             class="tab-bar-screen_tab_bar_item__fPG6j"
                             :class="{ 'tab-bar-screen_active__pBXjN': $route.path.startsWith('/favorite') }"
                >
                    <div class="tab-bar-screen_icon__xrTCK">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
                             viewBox="0 0 24 24"
                             fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                             stroke-linejoin="round" class="tabler-icon tabler-icon-heart ">
                            <path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"></path>
                        </svg>
                    </div>
                    <div class="nav-link">Избранное</div>
                </router-link>
                <router-link to="/cart"
                             class="tab-bar-screen_tab_bar_item__fPG6j"
                             :class="{ 'tab-bar-screen_active__pBXjN': $route.path.startsWith('/cart') }"
                >
                    <div class="tab-bar-screen_icon__xrTCK">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
                             viewBox="0 0 24 24"
                             fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                             stroke-linejoin="round" class="tabler-icon tabler-icon-basket ">
                            <path d="M10 14a2 2 0 1 0 4 0a2 2 0 0 0 -4 0"></path>
                            <path d="M5.001 8h13.999a2 2 0 0 1 1.977 2.304l-1.255 7.152a3 3 0 0 1 -2.966 2.544h-9.512a3 3 0 0 1 -2.965 -2.544l-1.255 -7.152a2 2 0 0 1 1.977 -2.304z"></path>
                            <path d="M17 10l-2 -6"></path>
                            <path d="M7 10l2 -6"></path>
                        </svg>
                    </div>
                    <div class="nav-link">Корзина</div>
                </router-link>
                <router-link to="/profile"
                             class="tab-bar-screen_tab_bar_item__fPG6j"
                             :class="{ 'tab-bar-screen_active__pBXjN': ['/profile', '/edit_profile'].some(path => $route.path.startsWith(path)) }"
                >
                    <div class="tab-bar-screen_icon__xrTCK">
                        <div class="index_page_settings_icon__hpJzL">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                                 xmlns="http://www.w3.org/2000/svg">
                                <path opacity="0.4"
                                      d="M12.1207 12.78C12.0507 12.77 11.9607 12.77 11.8807 12.78C10.1207 12.72 8.7207 11.28 8.7207 9.50998C8.7207 7.69998 10.1807 6.22998 12.0007 6.22998C13.8107 6.22998 15.2807 7.69998 15.2807 9.50998C15.2707 11.28 13.8807 12.72 12.1207 12.78Z"
                                      stroke="#292D32" stroke-width="1.5" stroke-linecap="round"
                                      stroke-linejoin="round"/>
                                <path opacity="0.34"
                                      d="M18.7398 19.3801C16.9598 21.0101 14.5998 22.0001 11.9998 22.0001C9.39977 22.0001 7.03977 21.0101 5.25977 19.3801C5.35977 18.4401 5.95977 17.5201 7.02977 16.8001C9.76977 14.9801 14.2498 14.9801 16.9698 16.8001C18.0398 17.5201 18.6398 18.4401 18.7398 19.3801Z"
                                      stroke="#292D32" stroke-width="1.5" stroke-linecap="round"
                                      stroke-linejoin="round"/>
                                <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"
                                      stroke="#292D32" stroke-width="1.5" stroke-linecap="round"
                                      stroke-linejoin="round"/>
                            </svg>
                        </div>
                    </div>
                    <div class="nav-link">Профиль</div>
                </router-link>
            </div>
        </div>
    </nav>
</template>

<script>
export default {
    name: "Navbar"
}













</script>

<style scoped>
.navbar {
    display: flex;
    justify-content: space-around;
    align-items: center;
    height: 60px;

    background-color: rgba(255, 255, 255, 0.8);
    background-filter: blur(10px);
    border-top: 1px solid #ccc;
}

.nav-link {
    text-decoration: none;
    color: #333;
    font-size: 16px;
    font-weight: 500;
}













</style>