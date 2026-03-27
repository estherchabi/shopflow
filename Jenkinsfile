// Jenkinsfile — ShopFlow CI/CD Pipeline
pipeline {
    agent any
    }

    environment {
        APP_NAME  = 'shopflow'
        // IMAGE_TAG sera défini dans le stage Build Docker
    }

    stages {
        // ← vos stages ici (parties 2, 3, 4)
        stage('Install') {
            steps {
                sh '''
                    pip install --upgrade pip -q
                    pip install -r requirements.txt -q
                    echo "Dépendances installées"
                '''
            }
        }
        stage('Lint') {
            steps {
                sh '''
                    flake8 app/ \
                        --max-line-length=100 \
                        --exclude=__init__.py \
                        --format=default
                '''
            }
            post {
                failure {
                    echo 'Lint échoué  corriger les erreurs PEP8'
                }
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh '''
                    pytest tests/unit/ \
                        -v \
                        -m unit \
                        --junitxml=junit-unit.xml \
                        --no-cov
                '''
            }
            post {
                always {
                    junit 'junit-unit.xml'   // publie les résultats dans Jenkins
                }
            }
        }

        stage('Integration Tests') {
            steps {
                sh '''
                    pytest tests/integration/ \
                        -v \
                        -m integration \
                        --junitxml=junit-integration.xml \
                        --no-cov
                '''
            }
            post {
                always {
                    junit 'junit-integration.xml'
                }
            }
        }

        stage('Coverage') {
            steps {
                sh '''
                    pytest tests/ \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=html:htmlcov \
                        --cov-report=term-missing \
                        --cov-fail-under=80 \
                        --junitxml=junit-report.xml
                '''
            }
            post {
                always {
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
                failure {
                    echo 'Coverage < 80% — ajouter des tests'
                }
            }
        }

    }


    post {
        always {
            echo 'Pipeline terminé'
        }
        success { echo 'Pipeline ShopFlow réussi' }
        failure { echo 'Pipeline ShopFlow échoué' }
    }
}
