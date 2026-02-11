// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import CatalogView from '../views/CatalogView.vue'
import ProductsView from '../views/ProductsView.vue'
import ProductDetailView from '../views/ProductDetailView.vue'
import CartView from '../views/CartView.vue'
import OrderView from '../views/OrderView.vue'
import FavoriteView from '../views/FavoriteView.vue'
import OrderHistoryView from '../views/OrderHistoryView.vue'
import ProfileView from '../views/ProfileView.vue'
import EditProfileView from '../views/EditProfileView.vue'

const routes = [
    {
        path: '/',
        name: 'Main',
        component: MainView
    },
    {
        path: '/catalog',
        name: 'Catalog',
        component: CatalogView
    },
    {
        path: '/products',
        name: 'Products',
        component: ProductsView
    },
    {
        path: '/product',
        name: 'Product',
        component: ProductDetailView
    },
    {
        path: '/cart',
        name: 'Cart',
        component: CartView
    },
    {
        path: '/order',
        name: 'Order',
        component: OrderView
    },
    {
        path: '/favorite',
        name: 'Favorite',
        component: FavoriteView
    },
    {
        path: '/orders_history',
        name: 'OrderHistoryView',
        component: OrderHistoryView
    },
    {
        path: '/profile',
        name: 'Profile',
        component: ProfileView
    },
    {
        path: '/edit_profile',
        name: 'EditProfile',
        component: EditProfileView
    }
]

const router = createRouter ({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes
})

export default router