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
  const currentRender = ++renderCount.value;
  const id = `camply-mermaid-${instanceId}-${currentRender}`;
  try {
    const { default: mermaid } = await import("mermaid");
    if (currentRender !== renderCount.value) {
      return;
    }
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: isDark.value ? "dark" : "default",
    });
    const result = await mermaid.render(id, source.value);
    if (currentRender !== renderCount.value) {
      return;
    }
    svg.value = result.svg;
    error.value = "";
  } catch (err) {
    if (currentRender !== renderCount.value) {
      return;
    }
    svg.value = "";
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    document.getElementById(`d${id}`)?.remove();
    document.getElementById(id)?.remove();
  }
}

onMounted(() => {
  void renderDiagram();
});

watch(source, () => {
  svg.value = "";
  error.value = "";
  void renderDiagram();
});

watch(isDark, () => {
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
