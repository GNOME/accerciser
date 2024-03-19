/*
 * @license: BSD
 *
 * All rights reserved. This program and the accompanying materials are made
 * available under the terms of the BSD which accompanies this distribution, and
 * is available at U{http://www.opensource.org/licenses/bsd-license.php}
 */

// JavaScript script to retrieve window information via KWin API

// build a JSON array containing one object for each window
json_output = "["
const clients = workspace.windowList();
for (var i = 0; i < clients.length; i++) {
  json_output += "\n  {";
  json_output += "\n\"caption\": \"" + clients[i].caption + "\"";
  json_output += ",\n\"bufferGeometry.x\": " + clients[i].bufferGeometry.x;
  json_output += ",\n\"bufferGeometry.y\": " + clients[i].bufferGeometry.y;
  json_output += ",\n\"bufferGeometry.width\": " + clients[i].bufferGeometry.width;
  json_output += ",\n\"bufferGeometry.height\": " + clients[i].bufferGeometry.height;
  json_output += "}"

  if (i < clients.length - 1)
    json_output += ","
}
json_output += "\n]"

print(json_output)
