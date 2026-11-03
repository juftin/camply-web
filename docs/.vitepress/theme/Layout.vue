<script setup lang="ts">
import DefaultTheme from "vitepress/theme";
import BackToApp from "./BackToApp.vue";

const { Layout } = DefaultTheme;
</script>

<template>
  <Layout>
    <template #nav-bar-content-after>
      <BackToApp variant="nav" />
    </template>
    <template #nav-screen-content-after>
      <BackToApp variant="mobile" />
    </template>
    <template #sidebar-nav-before>
      <BackToApp variant="sidebar" />
    </template>
  </Layout>
</template>
