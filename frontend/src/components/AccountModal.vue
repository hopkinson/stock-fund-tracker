<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
    <div class="bg-slate-900 border border-slate-800/80 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[85vh]">
      
      <!-- 头部：沉稳极简 -->
      <div class="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Layers class="w-4 h-4" />
          </div>
          <div>
            <h3 class="font-semibold text-slate-100 text-sm">
              持仓与平台同步
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">
              连接东方财富、天天基金、雪球，自动拉取持仓与成本
            </p>
          </div>
        </div>
        
        <div class="flex items-center space-x-2">
          <button 
            @click="triggerSyncAll"
            :disabled="syncingAll"
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center space-x-1.5 shadow-sm shadow-indigo-600/30 disabled:opacity-50"
            title="一键同步所有已绑定平台"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{'animate-spin': syncingAll}" />
            <span>{{ syncingAll ? '全量同步中...' : '一键全量同步' }}</span>
          </button>
          <button @click="$emit('close')" class="text-slate-400 hover:text-white transition p-1.5 rounded-lg hover:bg-slate-800">
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- 账户列表：去除盒式嵌套，统一层级 -->
      <div class="p-5 space-y-3 overflow-y-auto">
        <div 
          v-for="acc in accounts" 
          :key="acc.id" 
          class="rounded-xl border transition-all duration-200"
          :class="activeEditId === acc.id 
            ? 'bg-slate-950/80 border-slate-700 shadow-lg' 
            : 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700/80'"
        >
          <!-- 账户卡片摘要行 -->
          <div class="p-4 flex items-center justify-between gap-3">
            <div class="flex items-center space-x-3 min-w-0">
              <!-- 平台专属标识 -->
              <div class="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 select-none" :class="getPlatformBadge(acc.platform)">
                {{ getPlatformShort(acc.platform) }}
              </div>

              <div class="min-w-0">
                <div class="flex items-center space-x-2">
                  <span class="font-medium text-slate-200 text-sm tracking-tight">{{ acc.name }}</span>
                  <span 
                    class="px-2 py-0.5 text-[10px] rounded-full font-medium"
                    :class="getStatusBadgeClass(acc)"
                  >
                    {{ getStatusText(acc) }}
                  </span>
                </div>
                
                <div class="text-[11px] text-slate-400 font-mono mt-0.5 truncate">
                  资产: ¥{{ (acc.market_value || 0).toLocaleString() }} · {{ acc.position_count || 0 }} 个持仓
                  <span v-if="acc.last_sync_time" class="text-slate-500 ml-1.5">
                    · {{ formatTime(acc.last_sync_time) }} 同步
                  </span>
                </div>
              </div>
            </div>

            <!-- 右侧紧凑操作区 -->
            <div class="flex items-center space-x-1.5 shrink-0">
              <a 
                :href="getPlatformUrl(acc.platform)" 
                target="_blank" 
                rel="noopener noreferrer"
                class="px-2.5 py-1 text-xs font-medium rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition flex items-center space-x-1"
                title="在新窗口打开平台网页"
              >
                <span>打开网页</span>
                <ExternalLink class="w-3 h-3 opacity-70" />
              </a>

              <button 
                @click="toggleEdit(acc)"
                class="px-2.5 py-1 text-xs font-medium rounded-lg border transition"
                :class="activeEditId === acc.id 
                  ? 'bg-slate-800 text-slate-200 border-slate-600' 
                  : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800 hover:border-slate-700'"
              >
                {{ activeEditId === acc.id ? '收起' : '配置' }}
              </button>

              <button 
                @click="triggerSync(acc.id)"
                :disabled="syncingId === acc.id"
                class="p-1.5 rounded-lg bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 transition disabled:opacity-50"
                :title="syncingId === acc.id ? '同步中...' : '立即同步持仓'"
              >
                <RefreshCw class="w-3.5 h-3.5" :class="{'animate-spin text-indigo-300': syncingId === acc.id}" />
              </button>
            </div>
          </div>

          <!-- 异常信息条：轻量警示，无多层卡片感 -->
          <div 
            v-if="acc.sync_status === 'error' && acc.sync_message" 
            class="mx-4 mb-3 px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300 flex items-center justify-between"
          >
            <div class="flex items-center space-x-1.5 truncate">
              <AlertCircle class="w-3.5 h-3.5 shrink-0 text-rose-400" />
              <span class="truncate">{{ acc.sync_message }}</span>
            </div>
            <span class="text-rose-400/60 font-mono text-[10px] shrink-0 ml-2">
              {{ acc.last_sync_time ? formatTime(acc.last_sync_time) : '' }}
            </span>
          </div>

          <!-- 展开的凭证配置面板：纯净扁平，单动线设计 -->
          <div v-if="activeEditId === acc.id" class="px-4 pb-4 pt-2 border-t border-slate-800/60 space-y-3">
            
            <!-- 引导栏：水平步骤胶囊，消除大面积文字墙 -->
            <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 pt-1">
              <div class="flex items-center space-x-2">
                <span class="text-[11px] text-slate-400">两步获取:</span>
                
                <!-- 步骤1: 网页直达 -->
                <a 
                  :href="getPlatformUrl(acc.platform)" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-[11px] transition border border-slate-700/60"
                >
                  <span>1. 登录网页</span>
                  <ExternalLink class="w-2.5 h-2.5 opacity-60" />
                </a>

                <!-- 步骤2: 控制台一键复制代码 / 东财指引 -->
                <button 
                  type="button"
                  @click="copyCommandSnippet(acc.platform)"
                  class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] transition border font-mono"
                  :class="acc.platform === 'eastmoney' 
                    ? 'bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 border-amber-500/30'
                    : copied 
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                      : 'bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 border-indigo-500/30'"
                >
                  <AlertCircle v-if="acc.platform === 'eastmoney'" class="w-2.5 h-2.5 text-amber-400" />
                  <Check v-else-if="copied" class="w-2.5 h-2.5 text-emerald-400" />
                  <Copy v-else class="w-2.5 h-2.5 opacity-70" />
                  <span>{{ acc.platform === 'eastmoney' ? '2. 抓取说明(需Network面板)' : (copied ? '已复制命令' : '2. 复制抓取代码') }}</span>
                </button>
              </div>

              <span class="text-[10px] text-slate-400 font-mono">
                {{ acc.platform === 'eastmoney' ? '从网络面板复制 Cookie 标头' : '按 F12 粘贴回车即可' }}
              </span>
            </div>

            <!-- 东财专属提示条 -->
            <div v-if="acc.platform === 'eastmoney'" class="text-[11px] text-amber-300/90 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 space-y-1">
              <div class="font-medium flex items-center space-x-1 text-amber-400">
                <AlertCircle class="w-3.5 h-3.5" />
                <span>东财 Cookie 获取注意事项（含 HttpOnly）</span>
              </div>
              <p class="text-slate-300 leading-relaxed text-[11px]">
                东财交易会话 <code>ASP.NET_SessionId</code> 受安全防护，控制台脚本无法读取。请按 <strong>F12</strong> 打开开发者工具，切到 <strong>网络 (Network)</strong> 标签，点击页面左侧任意菜单，在网络请求的 <strong>标头 (Headers) -&gt; 请求标头 (Request Headers)</strong> 中复制完整的 <strong>Cookie</strong> 粘贴在下方。
              </p>
            </div>

            <!-- 输入框 -->
            <div>
              <textarea 
                v-model="editForm.cookie" 
                rows="2" 
                :placeholder="getCredentialPlaceholder(acc.platform)"
                class="w-full bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-xl p-3 font-mono placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none"
              ></textarea>
            </div>

            <!-- 底部操作栏：自动同步选项 + 单一主操作按钮 -->
            <div class="flex items-center justify-between pt-1">
              <label class="flex items-center space-x-2 text-xs text-slate-400 hover:text-slate-300 cursor-pointer select-none">
                <input 
                  type="checkbox" 
                  v-model="editForm.auto_sync" 
                  class="rounded bg-slate-800 border-slate-700 text-indigo-500 focus:ring-0 focus:ring-offset-0" 
                />
                <span>交易时间定时自动刷新</span>
              </label>

              <!-- 单一主按钮：保存并立即同步，免除二次点击困扰 -->
              <button 
                @click="saveAndSync(acc.id)"
                :disabled="savingAndSyncing"
                class="px-4 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition shadow-sm shadow-indigo-600/30 flex items-center space-x-1.5 disabled:opacity-50"
              >
                <RefreshCw v-if="savingAndSyncing" class="w-3 h-3 animate-spin" />
                <span>{{ savingAndSyncing ? '保存并同步中...' : '保存并立即同步' }}</span>
              </button>
            </div>

          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Layers, X, RefreshCw, ExternalLink, Copy, Check, AlertCircle } from 'lucide-vue-next'
import { getAccounts, updateAccount, syncAccount, syncAllAccounts } from '../api'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['close', 'refresh'])

const accounts = ref([])
const activeEditId = ref(null)
const syncingId = ref(null)
const syncingAll = ref(false)
const savingAndSyncing = ref(false)
const copied = ref(false)
const editForm = ref({ cookie: '', auto_sync: false })

const fetchAccounts = async () => {
  try {
    const res = await getAccounts()
    accounts.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

const toggleEdit = (acc) => {
  if (activeEditId.value === acc.id) {
    activeEditId.value = null
  } else {
    activeEditId.value = acc.id
    editForm.value = {
      cookie: acc.cookie || '',
      auto_sync: acc.auto_sync || false
    }
  }
}

const copyCommandSnippet = (platform) => {
  if (platform === 'eastmoney') {
    alert(
      '【东方财富 Cookie 获取提示】\n\n' +
      '由于东财交易端启用了 HttpOnly 安全机制，控制台无法通过 document.cookie 读取会话凭据。\n\n' +
      '请按以下步骤获取完整 Cookie：\n' +
      '1. 点击「1. 登录网页」登录东财交易系统 (jywg.18.cn)\n' +
      '2. 按 F12 打开开发者工具，切换到「网络 (Network)」标签\n' +
      '3. 点击页面左侧「查询」或「资金持仓」\n' +
      '4. 在网络列表中点击任意请求（如 Position 或任意 aspx 请求）\n' +
      '5. 在右侧「标头 (Headers)」找到「请求标头 (Request Headers)」中的 Cookie\n' +
      '6. 复制整串 Cookie（必须包含 ASP.NET_SessionId）粘贴到输入框即可。'
    )
    return
  }
  const code = 'copy(document.cookie)'
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(code)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } else {
    prompt('请复制以下命令粘贴到控制台回车：', code)
  }
}

// 统一主操作：保存并立即触发同步
const saveAndSync = async (id) => {
  savingAndSyncing.value = true
  try {
    await updateAccount(id, editForm.value)
    const syncRes = await syncAccount(id)
    activeEditId.value = null
    await fetchAccounts()
    emit('refresh')
    alert(syncRes.data?.message || '凭证保存并同步完成！')
  } catch (e) {
    alert('操作失败: ' + (e.response?.data?.message || e.message))
    await fetchAccounts()
  } finally {
    savingAndSyncing.value = false
  }
}

const triggerSync = async (id) => {
  syncingId.value = id
  try {
    const res = await syncAccount(id)
    alert(res.data?.message || '同步完成')
    await fetchAccounts()
    emit('refresh')
  } catch (e) {
    alert('同步失败: ' + (e.response?.data?.message || e.message))
    await fetchAccounts()
  } finally {
    syncingId.value = null
  }
}

const triggerSyncAll = async () => {
  syncingAll.value = true
  try {
    await syncAllAccounts()
    alert('全量同步触发成功！')
    await fetchAccounts()
    emit('refresh')
  } catch (e) {
    alert('同步失败: ' + (e.response?.data?.message || e.message))
  } finally {
    syncingAll.value = false
  }
}

const getPlatformUrl = (p) => {
  const map = {
    eastmoney: 'https://jywg.18.cn/',
    tiantian: 'https://tradeh5.1234567.com.cn/',
    xueqiu: 'https://xueqiu.com/',
    yangjibao: '#'
  }
  return map[p] || '#'
}

const getPlatformShort = (p) => {
  const map = { eastmoney: '东财', tiantian: '天天', xueqiu: '雪球', yangjibao: '养基' }
  return map[p] || '平台'
}

const getPlatformBadge = (p) => {
  const map = {
    eastmoney: 'bg-rose-500/15 text-rose-400 border border-rose-500/25',
    tiantian: 'bg-amber-500/15 text-amber-400 border border-amber-500/25',
    xueqiu: 'bg-blue-500/15 text-blue-400 border border-blue-500/25',
    yangjibao: 'bg-teal-500/15 text-teal-400 border border-teal-500/25'
  }
  return map[p] || 'bg-slate-800 text-slate-300'
}

const getStatusBadgeClass = (acc) => {
  if (acc.sync_status === 'error') {
    return 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
  }
  if (acc.has_cookie) {
    return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
  }
  return 'bg-slate-800/80 text-slate-400 border border-slate-700/60'
}

const getStatusText = (acc) => {
  if (acc.sync_status === 'error') return '需更新凭据'
  if (acc.has_cookie) return '已绑定'
  return '待绑定'
}

const getCredentialPlaceholder = (p) => {
  if (p === 'xueqiu') return '粘贴雪球 xq_a_token 或完整 Cookie...'
  if (p === 'tiantian') return '粘贴天天基金网页登录后抓取的整串 Cookie...'
  if (p === 'eastmoney') return '粘贴东方财富交易端登录后抓取的整串 Cookie...'
  if (p === 'yangjibao') return '粘贴养基宝小程序 Token，或直接粘贴持仓 JSON 文本...'
  return '在此粘贴凭证...'
}


const formatTime = (timeStr) => {
  if (!timeStr) return ''
  try {
    const d = new Date(timeStr)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

onMounted(() => {
  fetchAccounts()
})
</script>
