<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()

onMounted(async () => {
  if (auth.isLoggedIn && !auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      auth.logout()
    }
  }
})
</script>
