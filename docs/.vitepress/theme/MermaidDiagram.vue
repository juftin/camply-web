<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useData } from "vitepress";

const props = defineProps<{
  code: string;
}>();

const { isDark } = useData();
const svg = ref("");
const error = ref("");
const renderCount = ref(0);
const instanceId = Math.random().toString(36).slice(2, 10);

const source = computed(() => {
  try {
    return decodeURIComponent(props.code);
  } catch {
    return props.code;
  }
});

async function renderDiagram(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const { default: mermaid } = await import("mermaid");
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: isDark.value ? "dark" : "default",
    });
    renderCount.value += 1;
    const id = `camply-mermaid-${instanceId}-${renderCount.value}`;
    const result = await mermaid.render(id, source.value);
    svg.value = result.svg;
    error.value = "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

onMounted(() => {
  void renderDiagram();
});

watch([source, isDark], () => {
  void renderDiagram();
});
</script>

<template>
  <div class="camply-mermaid" data-mermaid-diagram="true">
    <div v-if="svg" class="camply-mermaid-svg" v-html="svg" />
    <pre v-else class="camply-mermaid-fallback"><code>{{ source }}</code></pre>
    <p v-if="error" class="camply-mermaid-error">{{ error }}</p>
  </div>
</template>
