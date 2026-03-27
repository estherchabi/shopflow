pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '--user root'
        }
    }

    environment {
        APP_NAME = 'shopflow'
    }

    stages {
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
                        --format=default || true
                '''
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
                    junit 'junit-unit.xml'
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
                    junit 'junit-report.xml'
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
                    echo 'Coverage < 80% - ajouter des tests'
                }
            }
        }

        stage('Static Analysis') {
            steps {
                sh '''
                    pylint app/ \
                        --output-format=parseable \
                        --exit-zero \
                        > pylint-report.txt || true

                    echo "Pylint terminé - voir pylint-report.txt"

                    bandit -r app/ \
                        -f json \
                        -o bandit-report.json \
                        --exit-zero

                    python3 -c "
import json, sys
data = json.load(open('bandit-report.json'))
high = [r for r in data.get('results', []) if r['issue_severity'] == 'HIGH']
if high:
    print(f'BANDIT: {len(high)} vuln HIGH détectée(s)')
    sys.exit(1)
print('BANDIT: aucune vulnérabilité HIGH')
"
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
                        docker run --rm \
                            --network host \
                            -v "$(pwd):/usr/src" \
                            -e SONAR_HOST_URL="${SONAR_HOST_URL}" \
                            -e SONAR_TOKEN="${SONAR_TOKEN}" \
                            sonarsource/sonar-scanner-cli \
                            sonar-scanner \
                                -Dsonar.projectKey=shopflow \
                                -Dsonar.sources=app \
                                -Dsonar.tests=tests \
                                -Dsonar.python.coverage.reportPaths=coverage.xml \
                                -Dsonar.python.pylint.reportPaths=pylint-report.txt
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }
    }

    post {
        always {
            echo 'Pipeline terminé'
        }
        success {
            echo 'Pipeline ShopFlow réussi'
        }
        failure {
            echo 'Pipeline ShopFlow échoué'
        }
    }
}