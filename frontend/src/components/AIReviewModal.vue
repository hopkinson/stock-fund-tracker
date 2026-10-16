<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150">
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <div class="w-7 h-7 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center">
            <Bot class="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 class="font-bold text-slate-100 text-sm">AI 资产配置与 ETF 持仓复盘</h3>
            <p class="text-[11px] text-slate-400">基于大模型 + 指数历史估值分位 + 场内折溢价率的 CIO 级专业诊断</p>
          </div>
        </div>
        <button @click="$emit('close')" class="text-slate-400 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
        <!-- API 配置折叠区 -->
        <div class="p-3 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-300 font-medium">大模型接口配置 (OpenAI 兼容)</span>
            <button @click="showConfig = !showConfig" class="text-indigo-400 hover:underline">
              {{ showConfig ? '收起配置' : (hasKey ? '已配置 Key (修改)' : '⚠️ 点击配置 API Key') }}
            </button>
          </div>
          <div v-if="showConfig" class="space-y-2 pt-2 border-t border-slate-800/80 text-xs">
            <div>
              <label class="block text-slate-400 mb-1 flex items-center justify-between">
                <span>API Key (推荐 DeepSeek)</span>
                <span v-if="maskedKey" class="text-emerald-400 text-[10px]">✓ 已生效: {{ maskedKey }}</span>
              </label>
              <input v-model="config.api_key" type="password" :placeholder="maskedKey ? maskedKey : 'sk-...'" class="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-1.5 font-mono focus:outline-none focus:border-indigo-500" />
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block text-slate-400 mb-1">Base URL</label>
                <input v-model="config.api_base" type="text" placeholder="https://api.deepseek.com/v1" class="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-1.5 font-mono text-[11px]" />
              </div>
              <div>
                <label class="block text-slate-400 mb-1">模型名称</label>
                <input v-model="config.model" type="text" placeholder="deepseek-chat" class="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-1.5 font-mono text-[11px]" />
              </div>
            </div>
            <div class="flex justify-end pt-1">
              <button @click="saveConfig" class="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition">保存 Key</button>
            </div>
          </div>
        </div>

        <!-- 针对性提问输入与快捷预设 -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-xs font-medium text-slate-300">对 AI 的特定指令 / 关注点</label>
            <span class="text-[10px] text-slate-500">点击下方快捷预设</span>
          </div>
          <div class="flex space-x-2">
            <input 
              v-model="customPrompt"
              type="text" 
              placeholder="如：诊断大类资产配置比例，哪些ETF低估适合加仓定投..." 
              class="flex-1 bg-slate-800 border border-slate-700 text-slate-100 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
              @keyup.enter="handleReview"
            />
            <button 
              @click="handleReview"
              :disabled="loading"
              class="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-medium rounded-xl shadow-md transition disabled:opacity-50 flex items-center space-x-1.5 shrink-0"
            >
              <Sparkles v-if="!loading" class="w-3.5 h-3.5" />
              <Loader2 v-else class="w-3.5 h-3.5 animate-spin" />
              <span>{{ loading ? 'CIO 诊断中...' : '生成复盘' }}</span>
            </button>
          </div>
          <!-- 快捷提示词标签 -->
          <div class="flex flex-wrap gap-1.5 mt-2">
            <button 
              v-for="chip in quickChips" 
              :key="chip" 
              @click="setQuickPrompt(chip)"
              class="px-2.5 py-1 bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white rounded-lg text-[11px] border border-slate-700/60 transition"
            >
              {{ chip }}
            </button>
          </div>
        </div>

        <!-- AI 输出结果展示 -->
        <div v-if="analysisResult" class="p-4 bg-slate-950/80 rounded-xl border border-purple-500/30 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
          {{ analysisResult }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Bot, X, Sparkles, Loader2 } from 'lucide-vue-next'
import axios from 'axios'

defineProps({ visible: Boolean })
defineEmits(['close'])

const showConfig = ref(false)
const hasKey = ref(false)
const maskedKey = ref('')
const config = ref({ api_key: '', api_base: 'https://api.deepseek.com/v1', model: 'deepseek-chat' })
const customPrompt = ref('')
const loading = ref(false)
const analysisResult = ref('')

const quickChips = [
  '🎯 诊断 ETF 大类配置比例与行业重叠度',
  '📊 哪些指数低估适合定投？哪些需止盈？',
  '⚠️ 检查场内溢价与伪分散风险',
  '🪜 制定分批定投/网格加仓点位',
  '⚡ 综合复盘与交易纪律点评'
]

const setQuickPrompt = (chip) => {
  customPrompt.value = chip
  handleReview()
}

const fetchConfig = async () => {
  try {
    const res = await axios.get('/api/ai/config')
    hasKey.value = res.data.has_key
    maskedKey.value = res.data.masked_key || ''
    if (res.data.api_base) config.value.api_base = res.data.api_base
    if (res.data.model) config.value.model = res.data.model
    if (!hasKey.value) showConfig.value = true
  } catch (e) {}
}

const saveConfig = async () => {
  try {
    await axios.post('/api/ai/config', config.value)
    hasKey.value = true
    showConfig.value = false
    await fetchConfig()
    alert('AI 配置保存成功！')
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const handleReview = async () => {
  loading.value = true
  analysisResult.value = ''
  try {
    const res = await axios.post('/api/ai/review', { prompt: customPrompt.value })
    analysisResult.value = res.data.analysis
  } catch (e) {
    analysisResult.value = '请求出错: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>
