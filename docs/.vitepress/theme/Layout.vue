<script setup lang="ts">
import { useData } from "vitepress";
import DefaultTheme from "vitepress/theme";
import BackToApp from "./BackToApp.vue";

const { Layout } = DefaultTheme;
const { theme } = useData();
</script>

<template>
  <Layout>
    <template #nav-bar-content-after>
      <BackToApp v-if="theme.showBackToApp" variant="nav" />
    </template>
    <template #nav-screen-content-after>
      <BackToApp v-if="theme.showBackToApp" variant="mobile" />
    </template>
    <template #sidebar-nav-before>
      <BackToApp v-if="theme.showBackToApp" variant="sidebar" />
    </template>
  </Layout>
</template>
