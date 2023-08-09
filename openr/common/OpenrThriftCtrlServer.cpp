/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#include <folly/logging/xlog.h>

#include <openr/common/Flags.h>
#include <openr/common/OpenrThriftCtrlServer.h>
namespace openr {

OpenrThriftCtrlServer::OpenrThriftCtrlServer(
    std::shared_ptr<const Config> config,
    std::shared_ptr<openr::OpenrCtrlHandler>& handler,
    std::shared_ptr<wangle::SSLContextConfig> sslContext)
    : config_{config}, ctrlHandler_{handler}, sslContext_{sslContext} {}

void
OpenrThriftCtrlServer::start() {
  // Please add your own implementation if you want to start the non default
  // thrift server.
  // Here we will only start the default one.
  startDefaultThriftServer();
}

void
OpenrThriftCtrlServer::stop() {
  // Stop & destroy thrift server. Will reduce ref-count on ctrlHandler
  for (auto& server : thriftCtrlServerVec_) {
    server->stop();
  }
  // Wait for all threads
  for (auto& thread : thriftCtrlServerThreadVec_) {
    thread.join();
  }
  for (auto& server : thriftCtrlServerVec_) {
    server.reset();
  }
}

void
OpenrThriftCtrlServer::startDefaultThriftServer() {
  auto server = setUpThriftServer();
  thriftCtrlServerThreadVec_.emplace_back(std::thread([&]() noexcept {
    XLOG(INFO) << "Starting ThriftCtrlServer thread ...";
    folly::setThreadName("openr-ThriftCtrlServer");
    server->serve();
    XLOG(INFO) << "ThriftCtrlServer thread got stopped.";
  }));

  // Wait until thrift server starts
  while (true) {
    auto evb = server->getServeEventBase();
    if (evb != nullptr and evb->isRunning()) {
      break;
    }
    std::this_thread::yield();
  }

  // Add to the server vector
  thriftCtrlServerVec_.emplace_back(std::move(server));
};

std::shared_ptr<apache::thrift::ThriftServer>
OpenrThriftCtrlServer::setUpThriftServer() {
  // Setup OpenrCtrl thrift server
  CHECK(ctrlHandler_);
  auto server = std::make_shared<apache::thrift::ThriftServer>();
  server->setInterface(ctrlHandler_);
  server->setNumIOWorkerThreads(1);
  // Intentionally kept this as (1). If you're changing to higher number please
  // address thread safety for private member variables in OpenrCtrlHandler
  server->setNumCPUWorkerThreads(1);
  // Enable TOS reflection on the server socket
  server->setTosReflect(true);
  // Set the port and interface for OpenrCtrl thrift server
  server->setPort(*config_->getThriftServerConfig().openr_ctrl_port());
  // Set workers join timeout.
  server->setWorkersJoinTimeout(std::chrono::seconds{
      *config_->getThriftServerConfig().workers_join_timeout()});
  // set streaming expiration time.
  server->setStreamExpireTime(
      std::chrono::milliseconds{FLAGS_stream_expire_time});

  // Setup TLS
  if (config_->isSecureThriftServerEnabled()) {
    setupThriftServerTls(
        *server,
        config_->getSSLThriftPolicy(),
        config_->getSSLSeedPath(),
        sslContext_);
  }
  return server;
};

void
OpenrThriftCtrlServer::startNonDefaultThriftServer() {
  XLOG(INFO)
      << "Please add your own implementation to start the non default thrift server.";
};

void
OpenrThriftCtrlServer::startVrfThread(
    bool isDefaultVrf, std::shared_ptr<apache::thrift::ThriftServer> server) {
  XLOG(INFO)
      << "Please add your own implementation to start the thread with Vrf.";
}

} // namespace openr
