pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '50'))
  }

  triggers {
    // jalan tiap 1 menit
    cron('H/1 * * * *')
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Setup Python') {
      steps {
        sh '''
          set -e
          python3 -V
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          pip install -r requirements.txt
        '''
      }
    }

    stage('Run Weather Monitor') {
      steps {
        sh '''
          set -e
          . .venv/bin/activate
          python monitor_weather.py
        '''
      }
    }

    stage('Archive Report') {
      steps {
        archiveArtifacts artifacts: 'reports/weather_report.txt', onlyIfSuccessful: false
      }
    }

    // --- Opsional: kirim Telegram bila ENV tersedia ---
stage('Notify Telegram') {
  steps {
    withCredentials([
      string(credentialsId: 'TELEGRAM_BOT_TOKEN', variable: 'BOT_TOKEN'),
      string(credentialsId: 'TELEGRAM_CHAT_ID',  variable: 'CHAT_ID')
    ]) {
      sh '''
        set -e
        # Ambil 30 baris terakhir dan batasi panjang <= 3500 karakter (limit Telegram 4096)
        tail -n 30 reports/weather_report.txt > /tmp/tg_msg.txt
        head -c 3500 /tmp/tg_msg.txt > /tmp/tg_msg_trimmed.txt

        # Kirim sebagai teks polos (tanpa parse_mode) agar aman dari formatting error
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
          -d "chat_id=${CHAT_ID}" \
          -d "disable_web_page_preview=true" \
          --data-urlencode "text@/tmp/tg_msg_trimmed.txt" \
          -o /tmp/telegram_resp.json || true

        echo "Telegram response:"
        cat /tmp/telegram_resp.json || true
      '''
    }
  }
}



    // --- Opsional: Email via Jenkins Mailer ---
    stage('Email (optional)') {
      when { expression { return env.EMAIL_TO?.trim() } }
      steps {
        emailext(
          subject: "Weather Report - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
          to: "${env.EMAIL_TO}",
          body: """<p>Ringkasan cuaca terbaru - (lihat Console Output & artifact):</p>
                   <pre>${readFile('reports/weather_report.txt')}</pre>""",
          mimeType: 'text/html'
        )
      }
    }
  }

  post {
    always { echo "Selesai. Cek Console Output & artifact weather_report.txt" }
  }
}
