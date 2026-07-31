export interface PresignResult {
  uploadUrl: string
  contentType: string
  accessUrl: string
}

export async function getPresignUrl(filename: string): Promise<PresignResult> {
  const response = await fetch(`/api/v1/oss/presign?filename=${encodeURIComponent(filename)}`)
  if (!response.ok) {
    throw new Error(`获取上传地址失败: ${response.status}`)
  }
  return response.json()
}

export async function uploadToOss(file: File, presign: PresignResult): Promise<void> {
  const uploadResponse = await fetch(presign.uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': presign.contentType,
    },
    body: file,
  })

  if (!uploadResponse.ok) {
    throw new Error(`上传图片失败: ${uploadResponse.status}`)
  }
}
