pipeline {
  agent any
  stages {
    stage('Sanity') {
      steps {
        echo "Declarative pipeline OK ✅"
        sh 'python3 -V || true'
      }
    }
  }
}
