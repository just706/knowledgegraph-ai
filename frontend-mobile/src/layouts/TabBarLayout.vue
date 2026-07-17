<template>
  <div class="tabbar-layout">
    <div class="content">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </div>

    <van-tabbar route fixed safe-area-inset-bottom>
      <van-tabbar-item to="/chat" icon="chat-o">AI助手</van-tabbar-item>
      <van-tabbar-item to="/knowledge" icon="description">知识库</van-tabbar-item>
      <van-tabbar-item to="/quiz" icon="edit">练习</van-tabbar-item>
      <van-tabbar-item to="/mistakes" icon="warning-o">错题本</van-tabbar-item>
      <van-tabbar-item to="/map" icon="share-o">知识地图</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup lang="ts">
// TabBar layout: 固定底部导航 + 内容区
</script>

<style scoped lang="scss">
.tabbar-layout {
  min-height: 100vh;
  padding-bottom: calc(50px + var(--kg-safe-bottom));
}

.content {
  min-height: calc(100vh - 50px - var(--kg-safe-bottom));
}
</style>
