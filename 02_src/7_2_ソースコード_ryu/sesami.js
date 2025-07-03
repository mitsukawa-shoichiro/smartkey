const axios = require('axios')
const aesCmac = require('node-aes-cmac').aesCmac

let wm2_cmd = async () => {
  try {
    let sesame_id = "11200413-0002-0611-3F00-9200FFFFFFFF"
    let key_secret_hex = 'daf80ccf3864885736250cd73849354c'
    let cmd = 88 //(toggle:88,lock:82,unlock:83)
    let base64_history = Buffer.from('test2').toString('base64')

    let sign = generateRandomTag(key_secret_hex)
    console.log('sign:', sign)
    let after_cmd = await axios({
      method: 'post',
      url: `https://app.candyhouse.co/api/sesame2/${sesame_id}/cmd`,
      headers: { 'x-api-key': "O3R8DiaBCR2CD8mi10ibR9yT5OMqZHByaDmSCmnT" },
      data: {
        cmd: cmd,
        history: base64_history,
        sign: sign,
      },
    })
    console.log('API:', after_cmd.data)
  } catch (err) {
    console.error('エラー:', err)
  }
}

function generateRandomTag(secret) {
  let key = Buffer.from(secret, 'hex')

  const date = Math.floor(Date.now() / 1000)
  const dateDate = Buffer.allocUnsafe(4)
  dateDate.writeUInt32LE(date)
  const message = Buffer.from(dateDate.slice(1, 4))

  return aesCmac(key, message)
}

wm2_cmd()