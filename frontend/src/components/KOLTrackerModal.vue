<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[88vh]">
      <!-- 头部 -->
      <div class="px-5 py-4 border-b border-slate-800 flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center">
            <Compass class="w-4 h-4 text-amber-400" />
          </div>
          <div>
            <h3 class="font-bold text-slate-100 text-sm">市场风向与板块动态</h3>
            <p class="text-[11px] text-slate-400">全自动汇总全市场热点与快讯，客观防追高，无需人工输入</p>
          </div>
        </div>
        <button @click="$emit('close')" class="text-slate-400 hover:text-white p-1 rounded-lg transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- 选项卡切换 -->
      <div class="px-5 pt-3 border-b border-slate-800/80 flex items-center justify-between text-xs font-medium shrink-0 bg-slate-950/40">
        <div class="flex items-center space-x-4">
          <button 
            @click="activeTab = 'boards'"
            class="pb-2.5 border-b-2 transition flex items-center space-x-1.5"
            :class="activeTab === 'boards' ? 'border-amber-400 text-amber-300' : 'border-transparent text-slate-400 hover:text-slate-200'"
          >
            <TrendingUp class="w-3.5 h-3.5" />
            <span>板块风向 ({{ boards.length }})</span>
          </button>
          <button 
            @click="activeTab = 'news'"
            class="pb-2.5 border-b-2 transition flex items-center space-x-1.5"
            :class="activeTab === 'news' ? 'border-amber-400 text-amber-300' : 'border-transparent text-slate-400 hover:text-slate-200'"
          >
            <Newspaper class="w-3.5 h-3.5" />
            <span>7x24 实时快讯 ({{ news.length }})</span>
          </button>
        </div>

        <button 
          @click="loadData" 
          :disabled="loading"
          class="pb-2.5 text-[11px] text-amber-400 hover:text-amber-300 flex items-center space-x-1 transition disabled:opacity-50"
        >
          <RefreshCw class="w-3 h-3" :class="{'animate-spin': loading}" />
          <span>{{ loading ? '刷新中...' : '刷新数据' }}</span>
        </button>
      </div>

      <!-- 内容主体 -->
      <div class="p-5 overflow-y-auto space-y-4 flex-1">
        <!-- 加载中状态 -->
        <div v-if="loading && boards.length === 0" class="py-12 flex flex-col items-center justify-center space-y-3 text-slate-400">
          <RefreshCw class="w-6 h-6 animate-spin text-amber-400" />
          <span class="text-xs">正在自动汇总全网热点与行情...</span>
        </div>

        <template v-else>
          <!-- 市场客观观察卡片（强调理性防追高） -->
          <div class="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 text-xs text-amber-200/90 flex items-start space-x-2.5 leading-relaxed">
            <ShieldAlert class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span class="font-bold text-amber-300 mr-1.5">【冷静观察】</span>
              <span>{{ summary || '全市场主要核心指数与行业 ETF 数据已自动同步，重点关注估值与仓位分散，切忌盲目跟风追高。' }}</span>
            </div>
          </div>

          <!-- 选项卡 1：板块动态与防追高提示 -->
          <div v-if="activeTab === 'boards'" class="space-y-2.5">
            <div 
              v-for="item in boards" 
              :key="item.code"
              class="p-3.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-slate-700 transition space-y-2"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                  <span class="font-bold text-xs sm:text-sm text-slate-100">{{ item.name }}</span>
                  <span class="text-xs text-slate-500 font-mono">{{ item.code }}</span>
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{{ item.category }}</span>
                  <span 
                    class="text-[10px] px-2 py-0.5 rounded font-medium border"
                    :class="getStatusClass(item.status_type)"
                  >
                    {{ item.status_tag }}
                  </span>
                </div>

                <div class="text-right">
                  <span class="text-xs font-mono font-bold text-slate-200">¥{{ item.current_price.toFixed(3) }}</span>
                  <span 
                    class="text-xs ml-2 font-mono font-bold"
                    :class="item.change_rate >= 0 ? 'text-red-400' : 'text-emerald-400'"
                  >
                    {{ item.change_rate >= 0 ? '+' : '' }}{{ item.change_rate.toFixed(2) }}%
                  </span>
                </div>
              </div>

              <!-- 估值与防追高提示 -->
              <div class="flex flex-col sm:flex-row sm:items-center justify-between text-[11px] pt-1 border-t border-slate-800/60 gap-1.5">
                <div class="text-slate-400 flex items-center space-x-2">
                  <span>估值: PE {{ item.pe }}</span>
                  <span v-if="item.pe_percentile !== null">
                    (历史分位 <strong :class="item.pe_percentile < 25 ? 'text-emerald-400' : (item.pe_percentile > 75 ? 'text-amber-400' : 'text-slate-300')">{{ item.pe_percentile }}%</strong>)
                  </span>
                </div>
                <div class="text-slate-400 text-[11px]">
                  💡 {{ item.hint }}
                </div>
              </div>
            </div>
          </div>

          <!-- 选项卡 2：7x24 实时快讯 -->
          <div v-else-if="activeTab === 'news'" class="space-y-2">
            <div v-if="news.length === 0" class="py-8 text-center text-xs text-slate-500">
              今日暂无重要快讯
            </div>
            <div 
              v-for="(item, idx) in news" 
              :key="idx"
              class="p-3 rounded-xl border border-slate-800 bg-slate-950/60 space-y-1 hover:border-slate-700 transition"
            >
              <div class="flex items-center space-x-2 text-[11px] text-slate-500">
                <Clock class="w-3 h-3 text-slate-400" />
                <span>{{ item.time }}</span>
              </div>
              <p class="text-xs text-slate-300 leading-relaxed">{{ item.text }}</p>
            </div>
          </div>
        </template>
      </div>

      <!-- 底部栏 -->
      <div class="px-5 py-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-500 shrink-0">
        <span>最后更新：{{ updatedAt || '实时同步中' }}</span>
        <button @click="$emit('close')" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition active:scale-95">
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Compass, X, TrendingUp, Newspaper, RefreshCw, ShieldAlert, Clock } from 'lucide-vue-next'
import { getMarketTrends } from '../api'

const props = defineProps({
  visible: Boolean
})
defineEmits(['close'])

const activeTab = ref('boards')
const loading = ref(false)
const summary = ref('')
const boards = ref([])
const news = ref([])
const updatedAt = ref('')

const getStatusClass = (type) => {
  switch (type) {
    case 'warning':
      return 'bg-amber-500/10 text-amber-300 border-amber-500/30'
    case 'up':
      return 'bg-red-500/10 text-red-400 border-red-500/30'
    case 'low_opp':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
    case 'down':
      return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
    default:
      return 'bg-slate-800 text-slate-400 border-slate-700'
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getMarketTrends()
    if (res.data.success) {
      summary.value = res.data.summary || ''
      boards.value = res.data.boards || []
      news.value = res.data.news || []
      updatedAt.value = res.data.updated_at || ''
    }
  } catch (e) {
    console.error('load market trends error:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val && boards.value.length === 0) {
    loadData()
  }
})

onMounted(() => {
  if (props.visible) {
    loadData()
  }
})
</script>
