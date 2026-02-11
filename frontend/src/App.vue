<template>
    <div class="app_container">
        <router-view />

        <Navbar />
    </div>
</template>

<script>
import Navbar from './components/Navbar.vue'

export default {
    name: 'App',
    components: {
        Navbar
    }
}
</script>

<style scoped>
</style>