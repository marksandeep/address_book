var myApp = angular.module('myApp', []);
/**
myApp.controller('AddressInfoController', ['$scope', function($scope) {
    $scope.address = {
        id: 1,
        name: 'Divesh',
        home_phone: 222590,
        work_phone: 222222
    };
}]);
**/
myApp.controller('AddressInfoController', ['$scope', '$http', function($scope, $http) {
    $http.get('http://127.0.0.1:8000/user').success(function(users){
        $scope.address = users;
    });
    $scope.displayInfo = function(){
        alert("Hello");
    }





}]);

var demoApp = angular.module('scopeInheritance', []);
demoApp.controller('MainController', ['$scope', function($scope) {
  $scope.timeOfDay = 'morning';
  $scope.name = 'Nikki';
}]);
demoApp.controller('ChildController', ['$scope', function($scope) {
  $scope.name = 'Mattie';
}]);
demoApp.controller('GrandChildController', ['$scope', function($scope) {
  $scope.timeOfDay = 'evening';
  $scope.name = 'Gingerbread Baby';
}]);