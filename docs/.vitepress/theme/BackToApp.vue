<script setup lang="ts">
import { ref, onMounted } from "vue";

defineProps<{
  variant?: "nav" | "sidebar" | "mobile";
}>();

const appUrl = ref("https://camply.rocks");

onMounted(() => {
  if (typeof window !== "undefined") {
    const isMirror =
      window.location.hostname === "juftin.com" ||
      window.location.hostname.endsWith(".github.io");
    if (!isMirror) {
      appUrl.value = "/";
    }
  }
});
</script>

<template>
  <!-- Sidebar variant: at the top of the sidebar navigation -->
  <div v-if="variant === 'sidebar'" class="sidebar-back-container">
    <a :href="appUrl" class="sidebar-back-link" target="_self">
      <span class="sidebar-back-arrow" aria-hidden="true">←</span>
      <span>Back to App</span>
    </a>
  </div>

  <!-- Mobile screen variant: in the mobile navigation menu -->
  <div v-else-if="variant === 'mobile'" class="mobile-back-container">
    <a :href="appUrl" class="mobile-back-button" target="_self">
      <span>Back to App</span>
      <span class="mobile-back-icon" aria-hidden="true">→</span>
    </a>
  </div>

  <!-- Navbar variant: prominent button in top navigation bar -->
  <div v-else class="nav-back-container">
    <a :href="appUrl" class="nav-back-button" target="_self">
      <span>Back to App</span>
      <svg
        class="nav-back-icon"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
        <polyline points="15 3 21 3 21 9" />
        <line x1="10" y1="14" x2="21" y2="3" />
      </svg>
    </a>
  </div>
</template>
