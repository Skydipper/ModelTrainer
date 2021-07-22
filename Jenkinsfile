#!groovy

node {

  // Actions
  def forceCompleteDeploy = false
  try {
    timeout(time: 15, unit: 'SECONDS') {
      forceCompleteDeploy = input(
        id: 'Proceed0', message: 'Force COMPLETE Deployment', parameters: [
        [$class: 'BooleanParameterDefinition', defaultValue: true, description: '', name: 'Please confirm you want to recreate services and deployments']
      ])
    }
  }
  catch(err) { // timeout reached or input false
      // nothing
  }

  // Variables
  def tokens = "${env.JOB_NAME}".tokenize('/')
  def dockerUsername = "${DOCKER_USERNAME}"
  def webserverImage = "${dockerUsername}/mt-webserver"
  def geotrainerImage = "${dockerUsername}/mt-geotrainer"

  currentBuild.result = "SUCCESS"

  checkout scm
  properties([pipelineTriggers([[$class: 'GitHubPushTrigger']])])

  try {

    stage ('Build Docker for Airflow Webserver') {
      sh("docker -H :2375 build -t ${webserverImage}:${env.BRANCH_NAME}.${env.BUILD_NUMBER} .")
      sh("docker -H :2375 build -t ${webserverImage}:latest .")
    }

    stage ('Build Docker for Geotrainer') {
      sh("docker -H :2375 build -t ${geotrainerImage}:${env.BRANCH_NAME}.${env.BUILD_NUMBER} ./api")
      sh("docker -H :2375 build -t ${geotrainerImage}:latest ./api")
    }

    stage('Push Docker') {
      withCredentials([usernamePassword(credentialsId: 'Skydipper Docker Hub', usernameVariable: 'DOCKER_HUB_USERNAME', passwordVariable: 'DOCKER_HUB_PASSWORD')]) {
        sh("docker -H :2375 login -u ${DOCKER_HUB_USERNAME} -p ${DOCKER_HUB_PASSWORD}")
        sh("docker -H :2375 push ${webserverImage}:${env.BRANCH_NAME}.${env.BUILD_NUMBER}")
        sh("docker -H :2375 push ${webserverImage}:latest")
        sh("docker -H :2375 push ${geotrainerImage}:${env.BRANCH_NAME}.${env.BUILD_NUMBER}")
        sh("docker -H :2375 push ${geotrainerImage}:latest")
        sh("docker -H :2375 rmi ${webserverImage}")
        sh("docker -H :2375 rmi ${geotrainerImage}")
      }
    }

    stage ("Deploy Application") {
      switch ("${env.BRANCH_NAME}") {

        // Roll out to production
        case "master":
            sh("echo Deploying to PROD cluster")
            sh("kubectl config use-context gke_${GCLOUD_PROJECT}_${GCLOUD_GCE_ZONE}_${KUBE_PROD_CLUSTER}")
            sh("kubectl apply -f api/k8s/services/")
            sh("kubectl apply -f api/k8s/production/")
            sh("kubectl set image deployment mt-geotrainer mt-geotrainer=${geotrainerImage}:${env.BRANCH_NAME}.${env.BUILD_NUMBER} --record")
            sh("kubectl set image deployment mt-webserver mt-webserver=${webserverImage}:${env.BRANCH_NAME}.${env.BUILD_NUMBER} --record")
          break

        // Default behavior?
        default:
          echo "Default -> do nothing"
          currentBuild.result = "SUCCESS"
      }
    }
  } catch (err) {

    currentBuild.result = "FAILURE"
    throw err
  }

}
