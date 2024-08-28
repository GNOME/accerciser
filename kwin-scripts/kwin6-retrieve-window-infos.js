/*
 * @license: BSD
 *
 * All rights reserved. This program and the accompanying materials are made
 * available under the terms of the BSD which accompanies this distribution, and
 * is available at U{http://www.opensource.org/licenses/bsd-license.php}
 */

// JavaScript script to retrieve window information via KWin API

const currentDesktop = workspace.currentDesktop;

let window_infos = [];
const clients = workspace.windowList();
for (let i = 0; i < clients.length; i++) {
  const isOnCurrentDesktop = clients[i].onAllDesktops || clients[i].desktops.includes(currentDesktop);

  const clientGeometry = clients[i].clientGeometry;
  const frameGeometry = clients[i].frameGeometry;
  // client geometry is used unless window has client side decorations,
  // in which case frame geometry is used;
  // assume that client side decoration is used when client rect contains the frame rect
  let geometry = clientGeometry;
  const clientContainsFrame =
      clientGeometry.x <= frameGeometry.x && clientGeometry.y <= frameGeometry.y
        && clientGeometry.x + clientGeometry.width >= frameGeometry.x + frameGeometry.width
        && clientGeometry.y + clientGeometry.height >= frameGeometry.y + frameGeometry.height;
  if (clientContainsFrame)
    geometry = frameGeometry;

  window_infos.push(
    {
      "caption": clients[i].caption,
      "bufferGeometry.x": clients[i].bufferGeometry.x,
      "bufferGeometry.y": clients[i].bufferGeometry.y,
      "bufferGeometry.width": clients[i].bufferGeometry.width,
      "bufferGeometry.height": clients[i].bufferGeometry.height,
      "desktopFileName": clients[i].desktopFileName,
      "geometry.x": geometry.x,
      "geometry.y": geometry.y,
      "geometry.width": geometry.width,
      "geometry.height": geometry.height,
      "isOnCurrentWorkspace": isOnCurrentDesktop,
      "pid": clients[i].pid,
      "stackingOrder": clients[i].stackingOrder
    }
  );
}

const json_output = JSON.stringify(window_infos);
console.info(json_output)
