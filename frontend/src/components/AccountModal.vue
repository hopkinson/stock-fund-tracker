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
              账户与持仓同步
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">
              绑定东方财富、天天基金、雪球、养基宝账号，自动同步持仓和成本
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
            <span>{{ syncingAll ? '正在同步...' : '一键全部同步' }}</span>
          </button>
          <button @click="$emit('close')" class="text-slate-400 hover:text-white transition p-1.5 rounded-lg hover:bg-slate-800" title="关闭">
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
                  市值: ¥{{ (acc.market_value || 0).toLocaleString() }} · {{ acc.position_count || 0 }} 只
                  <span v-if="acc.last_sync_time" class="text-slate-500 ml-1.5">
                    · {{ formatTime(acc.last_sync_time) }} 已同步
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
                title="去平台网页登录"
              >
                <span>去登录</span>
                <ExternalLink class="w-3 h-3 opacity-70" />
              </a>

              <button 
                @click="toggleEdit(acc)"
                class="px-2.5 py-1 text-xs font-medium rounded-lg border transition"
                :class="activeEditId === acc.id 
                  ? 'bg-slate-800 text-slate-200 border-slate-600' 
                  : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800 hover:border-slate-700'"
              >
                {{ activeEditId === acc.id ? '收起' : '设置' }}
              </button>

              <button 
                @click="triggerSync(acc.id)"
                :disabled="syncingId === acc.id"
                class="p-1.5 rounded-lg bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 transition disabled:opacity-50"
                :title="syncingId === acc.id ? '正在同步...' : '立即同步'"
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
                <span class="text-[11px] text-slate-400">两步搞定:</span>
                
                <!-- 步骤1: 网页直达 -->
                <a 
                  :href="getPlatformUrl(acc.platform)" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-[11px] transition border border-slate-700/60"
                >
                  <span>1. 打开网页登录</span>
                  <ExternalLink class="w-2.5 h-2.5 opacity-60" />
                </a>

                <!-- 步骤2: 控制台一键复制代码 / 东财指引 / 养基宝说明 -->
                <button 
                  type="button"
                  @click="copyCommandSnippet(acc.platform)"
                  class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] transition border font-mono"
                  :class="acc.platform === 'eastmoney' 
                    ? 'bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 border-amber-500/30' 
                    : acc.platform === 'yangjibao'
                      ? 'bg-teal-500/10 text-teal-300 hover:bg-teal-500/20 border-teal-500/30'
                      : copied 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                        : 'bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 border-indigo-500/30'"
                >
                  <AlertCircle v-if="acc.platform === 'eastmoney' || acc.platform === 'yangjibao'" class="w-2.5 h-2.5" :class="acc.platform === 'yangjibao' ? 'text-teal-400' : 'text-amber-400'" />
                  <Check v-else-if="copied" class="w-2.5 h-2.5 text-emerald-400" />
                  <Copy v-else class="w-2.5 h-2.5 opacity-70" />
                  <span>{{ { eastmoney: '2. 查看东财步骤', yangjibao: '2. 查看导入说明' }[acc.platform] || (copied ? '已复制代码' : '2. 复制提取代码') }}</span>
                </button>
              </div>

              <span class="text-[10px] text-slate-400 font-mono">
                {{ { eastmoney: '按 F12 从网络请求复制 Cookie 粘贴在下方', yangjibao: '直接粘贴 JSON 文本或 API Token' }[acc.platform] || '按 F12 粘贴回车即可' }}
              </span>
            </div>

            <!-- 东财专属提示条 -->
            <div v-if="acc.platform === 'eastmoney'" class="text-[11px] text-indigo-300/90 bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-2.5 space-y-1">
              <div class="font-medium flex items-center space-x-1 text-indigo-400">
                <Check class="w-3.5 h-3.5" />
                <span>东财持仓同步方法</span>
              </div>
              <p class="text-slate-300 leading-relaxed text-[11px]">
                按 <strong>F12</strong> 打开开发者工具，切到 <strong>网络 (Network)</strong> 标签，点击页面左侧任意菜单，在网络请求列表中找到 <code>queryAssetAndPositionV1</code>，复制其 <strong>请求标头中的 Cookie</strong>（或右键「以 fetch 格式复制」整段代码）直接粘贴在下方即可。
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
                <span>交易时间自动同步</span>
              </label>

              <!-- 单一主按钮：保存并立即同步 -->
              <button 
                @click="saveAndSync(acc.id)"
                :disabled="savingAndSyncing"
                class="px-4 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition shadow-sm shadow-indigo-600/30 flex items-center space-x-1.5 disabled:opacity-50"
              >
                <RefreshCw v-if="savingAndSyncing" class="w-3 h-3 animate-spin" />
                <span>{{ savingAndSyncing ? '正在同步...' : '保存并同步' }}</span>
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
      '【东方财富持仓凭据获取步骤】\n\n' +
      '1. 登录网页版交易端 (jywg.18.cn)\n' +
      '2. 按 F12 打开开发者工具，切换到「网络 (Network)」标签\n' +
      '3. 点击页面左侧「查询」或「资金持仓」\n' +
      '4. 在网络列表中找到 queryAssetAndPositionV1\n' +
      '5. 复制其请求标头中的 Cookie，或右键选择「以 fetch 格式复制」\n' +
      '6. 直接粘贴到输入框中保存即可自动同步！'
    )
    return
  }
  if (platform === 'yangjibao') {
    alert(
      '【养基宝持仓导入方式】\n\n' +
      '1. 支持直接粘贴养基宝导出的持仓 JSON 文本（包含基金代码、持有份额、成本价）\n' +
      '2. 或粘贴养基宝 API 接口地址与 Token（格式: 接口URL | Bearer Token）\n' +
      '3. 点击「保存并同步」即可自动解析并导入基金持仓！'
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
    alert(syncRes.data?.message || '保存并同步成功！')
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
    alert('已开始同步全部账户！')
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
  if (acc.sync_status === 'error') return '需更新'
  if (acc.has_cookie) return '已连接'
  return '未绑定'
}

const getCredentialPlaceholder = (p) => {
  if (p === 'xueqiu') return '粘贴雪球 Token 或完整 Cookie...'
  if (p === 'tiantian') return '粘贴天天基金网页 Cookie...'
  if (p === 'eastmoney') return '粘贴东方财富交易端 Cookie...'
  if (p === 'yangjibao') return '粘贴养基宝持仓 JSON 文本或 API Token...'
  return '在此粘贴...'
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
