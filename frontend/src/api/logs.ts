import { apiGet } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { OperationLog } from '@/types/log'

export const getOperationLogs = (params?: QueryParams) => apiGet<PageResult<OperationLog>>('/admin/logs', { params })
